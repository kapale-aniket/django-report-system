from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from domain.reports.interfaces import IReportRepository
from apps.reports.constants import (
    REPORT_FILE_INVALID_MESSAGE,
    REPORT_FILE_REQUIRED_MESSAGE,
    is_allowed_report_extension,
)
from apps.reports.infrastructure.models import (
    ActivityLog,
    DeadlineExtensionRequest,
    ReEvaluationRequest,
    Report,
)
from infrastructure.repositories.report_repository import (
    ActivityLogRepository,
    NotificationRepository,
    ReportRepository,
)
from application.services.notification_helper import queue_user_notification
from apps.reports.group_helpers import (
    notify_group_submission_stakeholders,
    notify_report_stakeholders,
    notify_teacher_for_report_submission,
    sync_group_report_teacher,
)
from application.services.project_group_service import ProjectGroupService
from apps.reports.settings_helpers import get_max_attempts_for_report, get_submission_deadline_for_report
from apps.reports.teacher_helpers import get_report_assigned_teacher, teacher_can_access_report, reports_for_teacher_q
from apps.reports.certificate_helpers import notify_admin_final_approval
from apps.reports.comment_helpers import post_report_comment
from infrastructure.database.activity_log import log_activity
from tasks.dispatch import (
    queue_report_ai_analysis,
    queue_report_submitted_email,
    queue_teacher_approved_email,
)
from core.exceptions.base import (
    BusinessLogicError,
    NotFoundAppError,
    PermissionAppError,
    ValidationAppError,
)
from core.services.base import BaseService

User = get_user_model()


class ReportService(BaseService):
    """Application service — all report business rules."""

    def __init__(
        self,
        report_repository: IReportRepository | None = None,
        activity_log_repository: ActivityLogRepository | None = None,
    ):
        self.report_repository: IReportRepository = report_repository or ReportRepository()
        self.activity_log_repository = activity_log_repository or ActivityLogRepository()
        self.repository = self.report_repository

    # --- access helpers ---

    def _student_can_act_on_report(self, user, report) -> bool:
        if report.student_id == user.id:
            return True
        if report.group_id and self.report_repository.student_in_group(report.group, user.id):
            return True
        return False

    def _can_view_report(self, user, report) -> bool:
        if report.is_deleted:
            return getattr(user, 'role', None) == User.Role.ADMIN
        role = getattr(user, 'role', None)
        if role == User.Role.ADMIN:
            return True
        if role == User.Role.TEACHER:
            return teacher_can_access_report(user, report)
        if role == User.Role.STUDENT:
            return self._student_can_act_on_report(user, report)
        return False

    def _get_report_or_404(self, report_id: int):
        report = self.report_repository.get_by_id(report_id)
        if report is None:
            raise NotFoundAppError('Report not found')
        return report

    def _get_report_detail_or_404(self, report_id: int):
        report = self.report_repository.get_detail(report_id)
        if report is None:
            raise NotFoundAppError('Report not found')
        return report

    def _ensure_view_access(self, user, report) -> None:
        if not self._can_view_report(user, report):
            raise PermissionAppError('You cannot access this report')

    def _mark_late_on_create(self, report) -> None:
        deadline = get_submission_deadline_for_report(report)
        if report.submitted_at and deadline:
            report.is_late_submission = report.submitted_at > deadline
            self.report_repository.update(report, {'is_late_submission': report.is_late_submission})

    def _mark_late_resubmit(self, report) -> None:
        deadline = get_submission_deadline_for_report(report)
        is_late = timezone.now() > deadline if deadline else False
        self.report_repository.update(report, {'is_late_submission': is_late})

    def _validate_file_size(self, uploaded_file) -> None:
        settings_obj = self.report_repository.get_system_settings()
        max_bytes = settings_obj.max_file_size_mb * 1024 * 1024
        if uploaded_file.size > max_bytes:
            raise ValidationAppError(
                f'File too large. Maximum size is {settings_obj.max_file_size_mb} MB.'
            )

    def _validate_report_file(self, uploaded_file) -> None:
        if not uploaded_file:
            raise ValidationAppError(REPORT_FILE_REQUIRED_MESSAGE)
        if not is_allowed_report_extension(getattr(uploaded_file, 'name', '')):
            raise ValidationAppError(REPORT_FILE_INVALID_MESSAGE)
        self._validate_file_size(uploaded_file)

    # --- list / detail ---

    def get_list_queryset(self, user):
        """Role-scoped queryset for list endpoints (filters applied in presentation)."""
        role = getattr(user, 'role', None)
        if role == User.Role.STUDENT:
            qs = self.report_repository.for_student(user)
            return qs.filter(is_deleted=False)
        if role == User.Role.TEACHER:
            return self.report_repository.for_teacher(user)
        if role == User.Role.ADMIN:
            return self.report_repository.for_admin()
        raise PermissionAppError('Invalid role for report list')

    def list_reports(self, user, filter_params: dict[str, Any] | None = None):
        qs = self.get_list_queryset(user)
        if filter_params:
            qs = self.report_repository.apply_search_filters(qs, filter_params)
        return qs

    def get_detail(self, user, report_id: int) -> dict[str, Any]:
        report = self._get_report_detail_or_404(report_id)
        self._ensure_view_access(user, report)
        self.report_repository.record_recent_view(user, report)

        role = getattr(user, 'role', None)
        settings_obj = self.report_repository.get_system_settings()
        pending_reeval = None
        if role == User.Role.STUDENT:
            pending_reeval = self.report_repository.get_pending_reevaluation(report, user)

        pending_extension = None
        if role == User.Role.STUDENT and self._student_can_act_on_report(user, report):
            pending_extension = self.report_repository.get_pending_extension(report, user)

        reeval_admin_queue = []
        if role == User.Role.ADMIN:
            reeval_admin_queue = list(
                self.report_repository.get_pending_reevaluations_for_report(report)
            )

        can_comment = (
            role in (User.Role.TEACHER, User.Role.ADMIN)
            or (role == User.Role.STUDENT and report.student_id == user.id)
        ) and not report.is_locked

        can_resubmit = (
            role == User.Role.STUDENT
            and self._student_can_act_on_report(user, report)
            and report.status == Report.Status.REJECTED
            and not report.is_locked
            and report.attempt_count < get_max_attempts_for_report(report, settings_obj)
        )

        return {
            'report': report,
            'bookmarked': self.report_repository.is_bookmarked(user, report.pk),
            'can_comment': can_comment,
            'can_resubmit': can_resubmit,
            'pending_reeval': pending_reeval,
            'pending_extension': pending_extension,
            'reeval_admin_queue': reeval_admin_queue,
            'rubric_rows': self.report_repository.get_rubric_rows(report),
            'settings': settings_obj,
            'report_max_attempts': get_max_attempts_for_report(report, settings_obj),
            'versions': list(self.report_repository.get_versions(report.pk)[:20]),
            'timeline': list(
                report.activity_logs.select_related('user').all()[:50]
            ),
        }

    def get_versions(self, user, report_id: int):
        report = self._get_report_or_404(report_id)
        self._ensure_view_access(user, report)
        return self.report_repository.get_versions(report_id)

    # --- student actions ---

    def submit_report(self, user, data: dict[str, Any]) -> Report:
        if getattr(user, 'role', None) != User.Role.STUDENT:
            raise PermissionAppError('Only students can submit reports')

        uploaded = data.get('file')
        self._validate_report_file(uploaded)

        group = None
        submission_type = data.get('submission_type', 'individual')
        assigned_teacher_id = user.assigned_teacher_id
        if submission_type == 'group':
            group_id = data.get('project_group_id')
            if not group_id:
                raise ValidationAppError('Select a project group for a group submission.')
            group_service = ProjectGroupService()
            group = group_service.resolve_group_for_submit(user, int(group_id))
            assigned_teacher_id = group.assigned_teacher_id

        rubric = self.report_repository.get_default_rubric()
        academic_year = (data.get('academic_year') or '').strip()
        if not academic_year:
            raise ValidationAppError('Academic year is required.')

        report = self.report_repository.create(
            {
                'student': user,
                'assigned_teacher_id': assigned_teacher_id,
                'title': data['title'],
                'file': uploaded,
                'tags': data.get('tags', ''),
                'group': group,
                'academic_year': academic_year,
                'submission_round': Report.SubmissionRound.REVIEW,
                'attempt_count': 1,
                'rubric': rubric,
            }
        )
        self._mark_late_on_create(report)
        log_activity(user, ActivityLog.Action.SUBMITTED, report)
        if group is not None:
            notify_group_submission_stakeholders(report, submitter=user)
        else:
            notify_report_stakeholders(
                report,
                f'Your report "{report.title}" was submitted successfully.',
                link=f'/reports/{report.pk}/',
            )
            notify_teacher_for_report_submission(report, submitter=user)
        queue_report_submitted_email(report.pk)
        queue_report_ai_analysis(report.pk)
        return report

    def resubmit_report(self, user, report_id: int, uploaded_file) -> Report:
        if getattr(user, 'role', None) != User.Role.STUDENT:
            raise PermissionAppError('Only students can resubmit reports')

        report = self._get_report_or_404(report_id)
        if not self._student_can_act_on_report(user, report):
            raise PermissionAppError('You cannot resubmit this report')

        if report.status != Report.Status.REJECTED:
            raise BusinessLogicError('You can only resubmit after rejection.')

        settings_obj = self.report_repository.get_system_settings()
        max_attempts = get_max_attempts_for_report(report, settings_obj)
        if report.attempt_count >= max_attempts:
            raise BusinessLogicError(
                f'Maximum submission attempts ({max_attempts}) reached.'
            )

        if not uploaded_file:
            raise ValidationAppError(REPORT_FILE_REQUIRED_MESSAGE)
        self._validate_report_file(uploaded_file)

        next_num = self.report_repository.next_version_number(report)
        self.report_repository.archive_current_file_as_version(report, next_num)

        report.file = uploaded_file
        report.status = Report.Status.PENDING
        report.teacher_approved = False
        report.admin_approved = False
        report.rejection_reason = ''
        report.certificate_generated = False
        report.is_final_submission = False
        report.attempt_count += 1
        report.submission_round = Report.SubmissionRound.REVIEW
        report.is_locked = False
        sync_group_report_teacher(report)
        report.save()

        self._mark_late_resubmit(report)
        log_activity(user, ActivityLog.Action.RESUBMITTED, report)
        if report.group_id:
            notify_group_submission_stakeholders(report, submitter=user, is_resubmit=True)
        else:
            notify_report_stakeholders(
                report,
                f'New version uploaded for "{report.title}".',
                link=f'/reports/{report.pk}/',
            )
            notify_teacher_for_report_submission(report, submitter=user, is_resubmit=True)
        queue_report_submitted_email(report.pk)
        report.ai_processing_status = Report.AIProcessingStatus.PENDING
        report.extracted_text = ''
        report.ai_analysis_json = {}
        report.ocr_verification_json = {}
        report.save(
            update_fields=[
                'ai_processing_status',
                'extracted_text',
                'ai_analysis_json',
                'ocr_verification_json',
            ]
        )
        queue_report_ai_analysis(report.pk)
        return report

    # --- teacher actions ---

    def teacher_approve(self, user, report_id: int, data: dict[str, Any]) -> Report:
        if getattr(user, 'role', None) != User.Role.TEACHER:
            raise PermissionAppError('Only teachers can approve reports')

        report = self._get_report_or_404(report_id)
        if not teacher_can_access_report(user, report):
            raise PermissionAppError('This report is not assigned to you')

        if report.status == Report.Status.REJECTED or report.is_locked:
            raise BusinessLogicError('Cannot approve this report in its current state.')

        teacher_marks = data.get('teacher_marks')
        if teacher_marks is not None and (teacher_marks < 0 or teacher_marks > 100):
            raise ValidationAppError('Teacher marks must be between 0 and 100.')

        report.teacher_marks = teacher_marks
        feedback = (data.get('feedback') or '').strip()
        report.feedback = feedback
        report.is_final_submission = bool(data.get('is_final_submission', False))
        report.teacher_approved = True
        report.refresh_status_from_flags()
        report.save()

        if feedback:
            post_report_comment(report, user, feedback)

        criterion_scores = data.get('criterion_scores') or {}
        if criterion_scores:
            int_scores = {int(k): v for k, v in criterion_scores.items()}
            self.report_repository.save_rubric_scores(report, int_scores)

        log_activity(user, ActivityLog.Action.TEACHER_APPROVED, report)
        notify_report_stakeholders(
            report,
            f'Teacher approved your report "{report.title}". Awaiting admin final approval.',
            link=f'/reports/{report.pk}/',
        )
        queue_teacher_approved_email(report.pk)
        return report

    def teacher_reject(self, user, report_id: int, reason: str) -> Report:
        if getattr(user, 'role', None) != User.Role.TEACHER:
            raise PermissionAppError('Only teachers can reject reports')

        report = self._get_report_or_404(report_id)
        if not teacher_can_access_report(user, report):
            raise PermissionAppError('This report is not assigned to you')

        reason = (reason or '').strip()
        if not reason:
            raise ValidationAppError('Rejection reason is required.')

        report.teacher_approved = False
        report.admin_approved = False
        report.status = Report.Status.REJECTED
        report.rejection_reason = reason
        report.is_locked = False
        report.submission_round = Report.SubmissionRound.REVIEW
        report.save()

        post_report_comment(report, user, reason)
        log_activity(user, ActivityLog.Action.TEACHER_REJECTED, report, detail=reason[:500])
        notify_report_stakeholders(
            report,
            f'Your report "{report.title}" was rejected by teacher. Reason sent by email.',
            link=f'/reports/{report.pk}/',
        )
        from tasks.celery_tasks.email_tasks import send_rejection_email_task

        send_rejection_email_task.delay(report.pk, reason)
        return report

    # --- admin actions ---

    def admin_approve(self, user, report_id: int, marks: int) -> Report:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can final-approve reports')

        report = self._get_report_or_404(report_id)
        if not report.teacher_approved:
            raise BusinessLogicError('Admin can approve only after teacher approval.')
        if report.status == Report.Status.REJECTED:
            raise BusinessLogicError('Report is rejected.')

        if marks < 0 or marks > 100:
            raise ValidationAppError('Final marks must be between 0 and 100.')

        report.marks = marks
        report.admin_approved = True
        report.refresh_status_from_flags()
        report.save()

        log_activity(user, ActivityLog.Action.ADMIN_APPROVED, report)
        log_activity(user, ActivityLog.Action.MARKS_SET, report, detail=f'Final marks: {report.marks}')
        notify_report_stakeholders(
            report,
            f'Final approval: "{report.title}" — marks {report.marks}.',
            link=f'/reports/{report.pk}/',
        )

        notify_admin_final_approval(report)
        return report

    def admin_reject(self, user, report_id: int, reason: str) -> Report:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can reject reports')

        report = self._get_report_or_404(report_id)
        reason = (reason or '').strip()
        if not reason:
            raise ValidationAppError('Rejection reason is required.')

        report.admin_approved = False
        report.teacher_approved = False
        report.status = Report.Status.REJECTED
        report.rejection_reason = reason
        report.is_locked = False
        report.submission_round = Report.SubmissionRound.REVIEW
        report.save()

        post_report_comment(report, user, reason)
        log_activity(user, ActivityLog.Action.ADMIN_REJECTED, report, detail=reason[:500])
        notify_report_stakeholders(report, f'Admin rejected "{report.title}".', link=f'/reports/{report.pk}/')
        from tasks.celery_tasks.email_tasks import send_rejection_email_task

        send_rejection_email_task.delay(report.pk, reason)
        return report

    def bulk_admin_approve_or_reject(self, user, report_ids: list[int], action: str, reason: str = '') -> dict[str, int]:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can perform bulk actions')

        if action not in ('approve', 'reject') or not report_ids:
            raise ValidationAppError('Invalid bulk action.')

        count = 0
        if action == 'approve':
            qs = self.report_repository.bulk_eligible_for_admin_approve(report_ids)
            for report in list(qs):
                if report.marks is None:
                    report.marks = report.teacher_marks or 0
                report.admin_approved = True
                report.refresh_status_from_flags()
                report.save()
                log_activity(user, ActivityLog.Action.ADMIN_APPROVED, report)
                notify_report_stakeholders(
                    report,
                    f'Bulk approval: "{report.title}" approved.',
                    link=f'/reports/{report.pk}/',
                )
                notify_admin_final_approval(report)
                count += 1
        else:
            reason = reason or 'Bulk rejection'
            for report in self.report_repository.get_reports_by_ids(report_ids):
                report.admin_approved = False
                report.teacher_approved = False
                report.status = Report.Status.REJECTED
                report.rejection_reason = reason
                report.is_locked = False
                report.save()
                log_activity(user, ActivityLog.Action.ADMIN_REJECTED, report, detail=reason[:500])
                count += 1
        return {'processed': count}

    def delete_report(self, user, report_id: int) -> Report:
        report = self._get_report_or_404(report_id)
        role = getattr(user, 'role', None)

        if role == User.Role.STUDENT:
            if report.student_id != user.id or report.status == Report.Status.APPROVED:
                raise BusinessLogicError('You cannot delete this report.')
        elif role not in (User.Role.TEACHER, User.Role.ADMIN):
            raise PermissionAppError('You cannot delete this report')

        report.is_deleted = True
        report.save(update_fields=['is_deleted'])
        log_activity(user, ActivityLog.Action.DELETED, report)
        return report

    def restore_report(self, user, report_id: int) -> Report:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can restore reports')

        report = self._get_report_or_404(report_id)
        report.is_deleted = False
        report.save(update_fields=['is_deleted'])
        log_activity(user, ActivityLog.Action.RESTORED, report)
        return report

    def assign_report_teacher(self, user, report_id: int, teacher_id: int | None) -> Report:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can assign project teachers')

        report = self._get_report_or_404(report_id)
        if report.group_id:
            group_service = ProjectGroupService()
            group_service.assign_teacher(user, report.group_id, teacher_id)
            report.refresh_from_db()
            teacher = report.assigned_teacher
            detail = teacher.username if teacher else 'none'
            log_activity(user, ActivityLog.Action.COMMENT, report, detail=f'Group project teacher updated: {detail}')
            return report

        teacher = None
        if teacher_id:
            teacher = User.objects.filter(pk=int(teacher_id), role=User.Role.TEACHER, is_active=True).first()
            if teacher is None:
                raise ValidationAppError('Invalid teacher selected.')

        report.assigned_teacher = teacher
        report.save(update_fields=['assigned_teacher'])
        detail = teacher.username if teacher else 'none'
        log_activity(user, ActivityLog.Action.COMMENT, report, detail=f'Project teacher assigned: {detail}')
        return report

    def add_comment(self, user, report_id: int, message: str):
        report = self._get_report_or_404(report_id)
        self._ensure_view_access(user, report)

        if report.is_locked and getattr(user, 'role', None) == User.Role.STUDENT:
            raise BusinessLogicError('This report is locked.')

        if getattr(user, 'role', None) == User.Role.STUDENT and not self._student_can_act_on_report(
            user, report
        ):
            raise PermissionAppError('You cannot comment on this report')

        message = (message or '').strip()
        if not message:
            raise ValidationAppError('Comment message is required.')

        comment = self.report_repository.create_comment(report, user, message)
        log_activity(user, ActivityLog.Action.COMMENT, report)

        if user == report.student:
            report_teacher = get_report_assigned_teacher(report)
            if report_teacher:
                queue_user_notification(
                    report_teacher,
                    f'New comment on "{report.title}"',
                    link=f'/reports/{report.pk}/',
                )
        else:
            notify_report_stakeholders(
                report,
                f'Your teacher commented on "{report.title}". Open the report to read the feedback.',
                link=f'/reports/{report.pk}/',
            )
        return comment

    def request_reevaluation(self, user, report_id: int, reason: str):
        if getattr(user, 'role', None) != User.Role.STUDENT:
            raise PermissionAppError('Only students can request re-evaluation')

        report = self._get_report_or_404(report_id)
        if report.student_id != user.id:
            raise PermissionAppError('You can only request re-evaluation for your own report')

        if report.status != Report.Status.APPROVED:
            raise BusinessLogicError('Re-evaluation applies to approved reports only.')

        if self.report_repository.get_pending_reevaluation(report, user):
            raise BusinessLogicError('A re-evaluation request is already pending.')

        reason = (reason or '').strip()
        if not reason:
            raise ValidationAppError('Reason is required.')

        req = self.report_repository.create_reevaluation_request(report, user, reason)
        log_activity(user, ActivityLog.Action.REEVAL_REQUESTED, report)
        for admin in User.objects.filter(role=User.Role.ADMIN):
            queue_user_notification(
                admin,
                f'Re-evaluation requested for "{report.title}"',
                link=f'/reports/{report.pk}/',
            )
        return req

    def resolve_reevaluation(self, user, reeval_id: int, action: str, updated_marks: int | None = None):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can resolve re-evaluation requests')

        req = self.report_repository.get_reevaluation_by_id(reeval_id)
        if req is None or req.status != ReEvaluationRequest.Status.PENDING:
            raise NotFoundAppError('Pending re-evaluation request not found')

        if action == 'approve':
            if updated_marks is None or updated_marks < 0 or updated_marks > 100:
                raise ValidationAppError('Updated marks (0–100) required for approval.')
            self.report_repository.resolve_reevaluation(
                req,
                status=ReEvaluationRequest.Status.APPROVED,
                updated_marks=updated_marks,
            )
            log_activity(
                user,
                ActivityLog.Action.REEVAL_RESOLVED,
                req.report,
                detail=f'Marks updated to {updated_marks}',
            )
            queue_user_notification(
                req.student,
                f'Re-evaluation approved. Updated marks: {updated_marks}',
                link=f'/reports/{req.report.pk}/',
            )
        elif action == 'reject':
            self.report_repository.resolve_reevaluation(
                req,
                status=ReEvaluationRequest.Status.REJECTED,
            )
            queue_user_notification(
                req.student,
                'Your re-evaluation request was declined.',
                link=f'/reports/{req.report.pk}/',
            )
        else:
            raise ValidationAppError('Invalid resolve action.')

        return req

    def request_extension(self, user, report_id: int, reason: str):
        if getattr(user, 'role', None) != User.Role.STUDENT:
            raise PermissionAppError('Only students can request extensions')

        report = self._get_report_or_404(report_id)
        if not self._student_can_act_on_report(user, report):
            raise PermissionAppError('You cannot request an extension for this report')

        if self.report_repository.get_pending_extension(report, user):
            raise BusinessLogicError('You already have a pending extension request.')

        reason = (reason or '').strip()
        if not reason:
            raise ValidationAppError('Reason is required.')

        return self.report_repository.create_extension_request(report, user, reason)

    def resolve_extension(self, user, extension_id: int, decision: str, note: str = ''):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can resolve extension requests')

        ext = self.report_repository.get_extension_by_id(extension_id)
        if ext is None:
            raise NotFoundAppError('Extension request not found')

        if decision not in ('approve', 'reject'):
            raise ValidationAppError('Invalid decision.')

        status = (
            DeadlineExtensionRequest.Status.APPROVED
            if decision == 'approve'
            else DeadlineExtensionRequest.Status.REJECTED
        )
        return self.report_repository.resolve_extension(
            ext,
            status=status,
            reviewed_by=user,
            admin_note=note,
        )

    def toggle_bookmark(self, user, report_id: int) -> bool:
        report = self._get_report_or_404(report_id)
        self._ensure_view_access(user, report)
        return self.report_repository.toggle_bookmark(user, report)

    def toggle_pin(self, user, report_id: int) -> Report:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can pin reports')

        report = self._get_report_or_404(report_id)
        report.is_pinned = not report.is_pinned
        report.save(update_fields=['is_pinned'])
        return report

    def get_certificate_bytes(self, user, report_id: int) -> bytes:
        from application.services.certificate_service import CertificateService

        report = self._get_report_or_404(report_id)
        self._ensure_view_access(user, report)
        return CertificateService(self.report_repository).get_certificate_for_user(user, report_id)

    # --- analytics / leaderboard / admin utilities ---

    def get_leaderboard(self, user, *, dept: str = '') -> dict[str, Any]:
        top_reports = list(self.report_repository.get_leaderboard_queryset(user, dept=dept)[:50])
        return {
            'top_reports': top_reports,
            'top_students': self.report_repository.get_top_students(limit=20),
            'department_rankings': self.report_repository.get_department_rankings(),
            'dept_filter': dept,
        }

    def get_analytics(self, user) -> dict[str, Any]:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can view analytics')
        return self.report_repository.get_analytics_stats()

    def get_system_settings(self, user):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can view system settings')
        return self.report_repository.get_system_settings()

    def update_system_settings(self, user, data: dict[str, Any]):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can update system settings')
        allowed = {
            'submission_deadline',
            'max_attempts',
            'max_file_size_mb',
            'group_submission_deadline',
            'group_max_attempts',
            'group_min_members',
            'group_max_members',
        }
        payload = {k: v for k, v in data.items() if k in allowed and v is not None}
        if not payload:
            raise ValidationAppError('No valid settings provided.')
        return self.report_repository.update_system_settings(payload)

    def get_activity_logs(self, user, filter_params: dict[str, Any] | None = None):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can view activity logs')
        qs = self.activity_log_repository.for_admin()
        if filter_params:
            qs = self.activity_log_repository.apply_filters(qs, filter_params)
        return qs

    def get_submission_tracking(self, user):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can view submission tracking')
        return self.report_repository.get_submission_tracking()

    def get_teacher_workload(self, user):
        if getattr(user, 'role', None) != User.Role.TEACHER:
            raise PermissionAppError('Only teachers can view workload')
        return self.report_repository.get_teacher_workload(user)

    def get_extension_queue(self, user):
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can view extension queue')
        return self.report_repository.get_pending_extensions()


class NotificationService(BaseService):
    """In-app notification operations."""

    repository_class = NotificationRepository

    def __init__(self, notification_repository: NotificationRepository | None = None):
        self.notification_repository = notification_repository or NotificationRepository()
        self.repository = self.notification_repository

    def list_notifications(self, user):
        return self.notification_repository.for_user(user)

    def mark_read(self, user, notification_id: int):
        notification = self.notification_repository.mark_read(notification_id, user)
        if notification is None:
            raise NotFoundAppError('Notification not found')
        return notification

    def mark_all_read(self, user) -> int:
        return self.notification_repository.mark_all_read(user)

    def delete_notification(self, user, notification_id: int) -> None:
        if not self.notification_repository.delete_for_user(notification_id, user):
            raise NotFoundAppError('Notification not found')
