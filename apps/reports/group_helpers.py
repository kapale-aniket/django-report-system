"""Project group creation, validation, and stakeholder notifications."""
from __future__ import annotations

from apps.accounts.infrastructure.models import User
from apps.reports.infrastructure.models import ProjectGroup, Report
from application.services.notification_helper import queue_user_notification
from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError, ValidationAppError


def parse_mate_ids(raw_value) -> list[int]:
    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple)):
        return [int(value) for value in raw_value if str(value).strip()]
    text = str(raw_value).strip()
    if not text:
        return []
    ids: list[int] = []
    for part in text.replace('[', '').replace(']', '').split(','):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def get_department_students(user, *, exclude_self: bool = True):
    department = (getattr(user, 'department', None) or '').strip()
    if not department:
        return User.objects.none()
    qs = User.objects.filter(
        role=User.Role.STUDENT,
        is_active=True,
        department=department,
    ).order_by('first_name', 'username')
    if exclude_self and user.pk:
        qs = qs.exclude(pk=user.pk)
    return qs


def get_teachers_for_department(department: str):
    department = (department or '').strip()
    qs = User.objects.filter(role=User.Role.TEACHER, is_active=True).order_by('first_name', 'username')
    if department:
        qs = qs.filter(department=department)
    return qs


def teacher_display_name(teacher) -> str:
    if teacher is None:
        return ''
    return teacher.get_full_name() or teacher.username


def teacher_display_with_department(teacher) -> str:
    if teacher is None:
        return ''
    name = teacher_display_name(teacher)
    department = (getattr(teacher, 'department', None) or '').strip()
    if department:
        return f'{name} ({department})'
    return name


def teacher_assignment_notification_message(teacher, group_name: str) -> str:
    teacher_label = teacher_display_with_department(teacher)
    return (
        f'Faculty guide assigned: {teacher_label} for your group "{group_name}". '
        f'You can submit the group project when ready.'
    )


def group_submission_member_notification_message(report, teacher) -> str:
    teacher_label = teacher_display_with_department(teacher)
    return (
        f'Your group project "{report.title}" was submitted and sent to '
        f'{teacher_label} for evaluation.'
    )


def teacher_submission_notification_message(report, *, submitter=None, is_resubmit: bool = False) -> str:
    submitter = submitter or report.student
    submitter_name = submitter.get_full_name() or submitter.username if submitter else 'A student'
    action = 'resubmitted' if is_resubmit else 'submitted'
    group_note = ''
    if report.group_id:
        group_name = getattr(report.group, 'name', '') or 'your group'
        group_note = f' (group: {group_name})'
    return (
        f'{submitter_name} {action} the project report "{report.title}"{group_note}. '
        f'Please review and evaluate.'
    )


def notify_group_teacher_assigned(group, teacher) -> None:
    """Notify every group member when admin assigns a faculty guide."""
    if teacher is None:
        notify_group_members(
            group,
            f'Teacher assignment was cleared for group "{group.name}".',
            link='/reports/groups/',
        )
        return
    message = teacher_assignment_notification_message(teacher, group.name)
    notify_group_members(group, message, link='/reports/groups/')


def notify_teacher_for_report_submission(report, *, submitter=None, is_resubmit: bool = False) -> None:
    from apps.reports.teacher_helpers import get_report_assigned_teacher

    teacher = get_report_assigned_teacher(report)
    if teacher is None:
        return
    message = teacher_submission_notification_message(
        report,
        submitter=submitter,
        is_resubmit=is_resubmit,
    )
    queue_user_notification(teacher, message, link=f'/reports/{report.pk}/')


def notify_group_submission_stakeholders(report, *, submitter=None, is_resubmit: bool = False) -> None:
    from apps.reports.teacher_helpers import get_report_assigned_teacher

    teacher = get_report_assigned_teacher(report)
    if report.group_id and teacher is not None:
        member_message = group_submission_member_notification_message(report, teacher)
        if is_resubmit:
            member_message = (
                f'A new version of your group project "{report.title}" was uploaded and sent to '
                f'{teacher_display_with_department(teacher)} for evaluation.'
            )
        notify_report_stakeholders(
            report,
            member_message,
            link=f'/reports/{report.pk}/',
            exclude_user=submitter,
        )
        if submitter is not None:
            queue_user_notification(
                submitter,
                member_message,
                link=f'/reports/{report.pk}/',
            )
    else:
        notify_report_stakeholders(
            report,
            f'Your report "{report.title}" was submitted successfully.',
            link=f'/reports/{report.pk}/',
            exclude_user=submitter,
        )
        if submitter is not None:
            queue_user_notification(
                submitter,
                f'Your report "{report.title}" was submitted successfully.',
                link=f'/reports/{report.pk}/',
            )
    notify_teacher_for_report_submission(report, submitter=submitter, is_resubmit=is_resubmit)


def validate_project_mates(submitter, mate_ids: list[int]) -> list[User]:
    from apps.reports.settings_helpers import get_group_project_rules

    department = (getattr(submitter, 'department', None) or '').strip()
    if not department:
        raise ValidationAppError('Set your department on your profile before creating a group project.')

    rules = get_group_project_rules()
    min_members = rules['min_members']
    max_members = rules['max_members']
    min_mates = max(min_members - 1, 0)
    max_mates = max(max_members - 1, 0)

    if len(mate_ids) < min_mates:
        raise ValidationAppError(
            f'Select at least {min_mates} project mate(s). Groups must have {min_members}–{max_members} members.'
        )

    if len(mate_ids) > max_mates:
        raise ValidationAppError(
            f'Select at most {max_mates} project mate(s). Groups must have {min_members}–{max_members} members.'
        )

    if not mate_ids and min_mates > 0:
        raise ValidationAppError('Select at least one project mate for a group.')

    if submitter.pk in mate_ids:
        raise ValidationAppError('You are already included — select other project mates only.')

    mates = list(
        User.objects.filter(
            pk__in=mate_ids,
            role=User.Role.STUDENT,
            is_active=True,
            department=department,
        )
    )
    if len(mates) != len(set(mate_ids)):
        raise ValidationAppError('Project mates must be active students from your department.')

    total_members = 1 + len(mates)
    if total_members < min_members or total_members > max_members:
        raise ValidationAppError(
            f'Groups must have between {min_members} and {max_members} members (you plus selected mates).'
        )

    return mates


def create_project_group(creator, name: str, mate_ids: list[int], *, description: str = '') -> ProjectGroup:
    """Create a public project group before any report is submitted."""
    mates = validate_project_mates(creator, mate_ids)
    department = (getattr(creator, 'department', None) or '').strip()
    group = ProjectGroup.objects.create(
        name=name.strip()[:200],
        description=(description or '').strip()[:2000],
        department=department,
        creator=creator,
        is_public=True,
    )
    group.members.set([creator, *mates])
    return group


def validate_group_for_submission(user, group_id: int) -> ProjectGroup:
    """Ensure the student can submit a new report for this group."""
    group = ProjectGroup.objects.filter(pk=group_id).prefetch_related('members').first()
    if group is None:
        raise NotFoundAppError('Project group not found.')

    if not group.members.filter(pk=user.pk).exists():
        raise PermissionAppError('You are not a member of this project group.')

    if not group.assigned_teacher_id:
        raise ValidationAppError(
            'No teacher has been assigned to this group yet. Ask an admin to assign a teacher before submitting.'
        )

    if group.has_active_submission:
        active = group.get_active_report()
        raise BusinessLogicError(
            'This group already has a submitted project. '
            'Other members should use Resubmit on the existing report if it was rejected.'
        )

    return group


def notify_group_members(group, message: str, link: str = '', exclude_user=None) -> None:
    for member in group.members.all():
        if exclude_user and member.pk == exclude_user.pk:
            continue
        queue_user_notification(member, message, link)


def report_stakeholder_ids(report, *, exclude_user=None) -> set[int]:
    user_ids: set[int] = set()
    if report.student_id:
        user_ids.add(report.student_id)
    if report.group_id:
        user_ids.update(report.group.members.values_list('pk', flat=True))
    if exclude_user and getattr(exclude_user, 'pk', None):
        user_ids.discard(exclude_user.pk)
    return user_ids


def report_stakeholder_users(report):
    user_ids = report_stakeholder_ids(report)
    if not user_ids:
        return []
    return list(User.objects.filter(pk__in=user_ids).order_by('first_name', 'username'))


def notify_report_stakeholders(report, message: str, link: str = '', exclude_user=None) -> None:
    """Queue in-app notifications for the submitter and all group members."""
    for user_id in report_stakeholder_ids(report, exclude_user=exclude_user):
        user = User.objects.filter(pk=user_id).first()
        if user:
            queue_user_notification(user, message, link)


def notify_report_stakeholders_sync(report, message: str, link: str = '', exclude_user=None) -> None:
    """Create in-app notifications immediately (server-rendered views)."""
    from apps.reports.notifications import create_in_app_notification

    for user_id in report_stakeholder_ids(report, exclude_user=exclude_user):
        user = User.objects.filter(pk=user_id).first()
        if user:
            create_in_app_notification(user, message, link)


def sync_group_report_teacher(report) -> None:
    """Keep group report assigned to the group's faculty guide."""
    if not report.group_id:
        return
    group = report.group
    if group is None:
        return
    if group.assigned_teacher_id and report.assigned_teacher_id != group.assigned_teacher_id:
        report.assigned_teacher_id = group.assigned_teacher_id
        report.save(update_fields=['assigned_teacher'])
