from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch

from apps.reports.group_helpers import (
    create_project_group,
    get_department_students,
    get_teachers_for_department,
    notify_group_members,
    notify_group_teacher_assigned,
    validate_group_for_submission,
)
from apps.reports.infrastructure.models import ProjectGroup
from core.exceptions.base import NotFoundAppError, PermissionAppError, ValidationAppError

User = get_user_model()


class ProjectGroupService:
    """Create public project groups, assign teachers, and validate group submissions."""

    def _group_queryset(self):
        return ProjectGroup.objects.prefetch_related(
            Prefetch('members', queryset=User.objects.order_by('first_name', 'username')),
            'assigned_teacher',
            'creator',
        ).annotate(member_total=Count('members', distinct=True))

    def list_public_groups(self, user, *, department: str = '') -> list[ProjectGroup]:
        qs = self._group_queryset().filter(is_public=True)
        department = (department or '').strip()
        if department:
            qs = qs.filter(department__iexact=department)
        return list(qs.order_by('-created_at', 'name')[:200])

    def list_my_groups(self, user) -> list[ProjectGroup]:
        if getattr(user, 'role', None) != User.Role.STUDENT:
            raise PermissionAppError('Only students can list their project groups.')
        return list(
            self._group_queryset()
            .filter(members=user)
            .order_by('-created_at', 'name')
        )

    def list_groups_for_admin(self, user, *, department: str = '') -> list[ProjectGroup]:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can manage project groups.')
        qs = self._group_queryset()
        department = (department or '').strip()
        if department:
            qs = qs.filter(department__iexact=department)
        return list(qs.order_by('-created_at', 'name')[:500])

    def get_group(self, user, group_id: int) -> ProjectGroup:
        group = self._group_queryset().filter(pk=group_id).first()
        if group is None:
            raise NotFoundAppError('Project group not found.')
        role = getattr(user, 'role', None)
        if role == User.Role.ADMIN:
            return group
        if group.is_public or group.members.filter(pk=user.pk).exists():
            return group
        raise PermissionAppError('You cannot view this project group.')

    def create_group(self, user, data: dict[str, Any]) -> ProjectGroup:
        if getattr(user, 'role', None) != User.Role.STUDENT:
            raise PermissionAppError('Only students can create project groups.')

        name = (data.get('name') or '').strip()
        if not name:
            raise ValidationAppError('Group name is required.')

        mate_ids = data.get('project_mate_ids_list')
        if mate_ids is None:
            from apps.reports.group_helpers import parse_mate_ids

            mate_ids = parse_mate_ids(data.get('project_mate_ids'))

        description = (data.get('description') or '').strip()
        group = create_project_group(user, name, mate_ids, description=description)
        notify_group_members(
            group,
            f'You were added to project group "{group.name}".',
            link='/reports/groups/',
            exclude_user=user,
        )
        return group

    def submittable_groups_for_user(self, user) -> list[ProjectGroup]:
        """Groups the student can submit to: member, teacher assigned, no active report."""
        if getattr(user, 'role', None) != User.Role.STUDENT:
            return []
        return list(
            self._group_queryset()
            .filter(
                members=user,
                assigned_teacher__isnull=False,
            )
            .exclude(
                reports__is_deleted=False,
            )
            .distinct()
            .order_by('name')
        )

    def resolve_group_for_submit(self, user, group_id: int) -> ProjectGroup:
        return validate_group_for_submission(user, group_id)

    def teachers_for_group(self, group: ProjectGroup):
        return get_teachers_for_department(group.department)

    def assign_teacher(self, user, group_id: int, teacher_id: int | None) -> ProjectGroup:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can assign group teachers.')

        group = ProjectGroup.objects.filter(pk=group_id).first()
        if group is None:
            raise NotFoundAppError('Project group not found.')

        teacher = None
        if teacher_id:
            teacher = User.objects.filter(pk=int(teacher_id), role=User.Role.TEACHER, is_active=True).first()
            if teacher is None:
                raise ValidationAppError('Invalid teacher selected.')
            group_department = (group.department or '').strip()
            teacher_department = (getattr(teacher, 'department', None) or '').strip()
            if group_department and teacher_department and group_department.lower() != teacher_department.lower():
                raise ValidationAppError(
                    f'Selected teacher belongs to {teacher_department}; group department is {group_department}.'
                )

        group.assigned_teacher = teacher
        group.save(update_fields=['assigned_teacher'])

        active_report = group.get_active_report()
        if active_report is not None:
            active_report.assigned_teacher = teacher
            active_report.save(update_fields=['assigned_teacher'])

        # Keep any other non-deleted group reports aligned with the group teacher.
        from apps.reports.infrastructure.models import Report

        Report.objects.filter(group=group, is_deleted=False).exclude(pk=getattr(active_report, 'pk', None)).update(
            assigned_teacher=teacher,
        )

        notify_group_teacher_assigned(group, teacher)
        return group
