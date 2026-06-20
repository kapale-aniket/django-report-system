from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Avg, Count, Max, Q, QuerySet
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.reports.infrastructure.models import (
    Comment,
    DeadlineExtensionRequest,
    Notification,
    ProjectGroup,
    ReEvaluationRequest,
    Report,
    ReportBookmark,
    ReportRecentView,
    ReportVersion,
    Rubric,
    SystemSettings,
)
from core.repositories.base import BaseRepository

User = get_user_model()


class ReportRepository(BaseRepository[Report]):
    model_class = Report

    def get_queryset(self):
        return super().get_queryset().select_related('student')

    def get_detail(self, id: int):
        return (
            self.model_class.objects.select_related(
                'student',
                'student__assigned_teacher',
                'assigned_teacher',
                'group',
                'rubric',
            )
            .prefetch_related('comments__user', 'group__members')
            .filter(pk=id)
            .first()
        )

    def for_student(self, user) -> QuerySet:
        return self.model_class.objects.filter(
            Q(student=user) | Q(group__members=user)
        ).distinct()

    def for_teacher(self, user) -> QuerySet:
        from apps.reports.teacher_helpers import reports_for_teacher_q

        return self.model_class.objects.filter(reports_for_teacher_q(user))

    def for_admin(self) -> QuerySet:
        return self.model_class.objects.all()

    def scoped_for_user(self, user) -> QuerySet:
        role = getattr(user, 'role', None)
        if role == User.Role.ADMIN:
            return self.for_admin()
        if role == User.Role.TEACHER:
            return self.for_teacher(user)
        return self.for_student(user)

    def apply_search_filters(self, qs: QuerySet, params: dict[str, Any]) -> QuerySet:
        """Filter queryset using dict params (mirrors legacy ReportFilterForm)."""
        search_query = (params.get('search') or '').strip()
        status_filter = params.get('status') or ''
        department_filter = (params.get('department') or '').strip()
        min_marks = params.get('min_marks')
        max_marks = params.get('max_marks')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        include_deleted = params.get('include_deleted', False)
        academic_year_filter = (params.get('academic_year') or '').strip()
        include_archived = params.get('include_archived', False)

        if not include_deleted:
            qs = qs.filter(is_deleted=False)
        if search_query:
            qs = qs.filter(
                Q(title__icontains=search_query)
                | Q(student__username__icontains=search_query)
                | Q(student__first_name__icontains=search_query)
                | Q(student__last_name__icontains=search_query)
                | Q(tags__icontains=search_query)
            )
        if department_filter:
            qs = qs.filter(student__department__icontains=department_filter)
        if status_filter == Report.Status.PENDING:
            qs = qs.filter(status=Report.Status.PENDING)
        elif status_filter == Report.Status.APPROVED:
            qs = qs.filter(status=Report.Status.APPROVED)
        elif status_filter == Report.Status.REJECTED:
            qs = qs.filter(status=Report.Status.REJECTED)
        elif status_filter == 'awaiting_admin':
            qs = qs.filter(
                teacher_approved=True,
                admin_approved=False,
                status=Report.Status.PENDING,
            )
        elif status_filter:
            qs = qs.filter(status=status_filter)
        if min_marks is not None:
            qs = qs.filter(marks__gte=min_marks)
        if max_marks is not None:
            qs = qs.filter(marks__lte=max_marks)
        if date_from:
            qs = qs.filter(submitted_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(submitted_at__date__lte=date_to)
        if academic_year_filter:
            qs = qs.filter(academic_year__icontains=academic_year_filter)
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return qs.order_by('-is_pinned', '-submitted_at')

    def get_versions(self, report_id: int) -> QuerySet:
        return ReportVersion.objects.filter(report_id=report_id).order_by('-version_number')

    def archive_current_file_as_version(self, report, next_version_number: int) -> ReportVersion:
        with report.file.open('rb') as fh:
            archived = fh.read()
        base_name = report.file.name.rsplit('/', maxsplit=1)[-1]
        rv = ReportVersion(report=report, version_number=next_version_number)
        rv.file.save(f'v{next_version_number}_{base_name}', ContentFile(archived), save=True)
        return rv

    def next_version_number(self, report) -> int:
        m = report.versions.aggregate(Max('version_number'))['version_number__max']
        return (m or 0) + 1

    def create_comment(self, report, user, message: str) -> Comment:
        return Comment.objects.create(report=report, user=user, message=message)

    def toggle_bookmark(self, user, report) -> bool:
        obj, created = ReportBookmark.objects.get_or_create(user=user, report=report)
        if not created:
            obj.delete()
            return False
        return True

    def is_bookmarked(self, user, report_id: int) -> bool:
        return ReportBookmark.objects.filter(user=user, report_id=report_id).exists()

    def record_recent_view(self, user, report) -> None:
        rv, created = ReportRecentView.objects.get_or_create(user=user, report=report)
        if not created:
            ReportRecentView.objects.filter(pk=rv.pk).update(viewed_at=timezone.now())

    def save_rubric_scores(self, report, scores: dict[int, int]) -> None:
        if not report.rubric_id:
            return
        stored: dict[str, int] = dict(report.rubric_scores_json or {})
        for crit in report.rubric.iter_criteria():
            crit_id = crit.pk
            if crit_id in scores:
                val = max(0, min(scores[crit_id], crit.max_score))
                stored[str(crit_id)] = val
        report.rubric_scores_json = stored
        report.save(update_fields=['rubric_scores_json'])

    def get_pending_reevaluation(self, report, student):
        return ReEvaluationRequest.objects.filter(
            report=report,
            student=student,
            status=ReEvaluationRequest.Status.PENDING,
        ).first()

    def get_pending_reevaluations_for_report(self, report) -> QuerySet:
        return ReEvaluationRequest.objects.filter(
            report=report,
            status=ReEvaluationRequest.Status.PENDING,
        ).select_related('student')

    def create_reevaluation_request(self, report, student, reason: str):
        return ReEvaluationRequest.objects.create(
            report=report,
            student=student,
            reason=reason,
        )

    def get_reevaluation_by_id(self, reeval_id: int):
        return ReEvaluationRequest.objects.select_related('report', 'student').filter(pk=reeval_id).first()

    def resolve_reevaluation(self, reeval, *, status: str, updated_marks: int | None = None):
        reeval.status = status
        reeval.resolved_at = timezone.now()
        if updated_marks is not None:
            reeval.updated_marks = updated_marks
        reeval.save()
        if status == ReEvaluationRequest.Status.APPROVED and updated_marks is not None:
            report = reeval.report
            report.marks = updated_marks
            report.save(update_fields=['marks'])
        return reeval

    def get_pending_extension(self, report, student):
        return DeadlineExtensionRequest.objects.filter(
            report=report,
            student=student,
            status=DeadlineExtensionRequest.Status.PENDING,
        ).first()

    def create_extension_request(self, report, student, reason: str):
        return DeadlineExtensionRequest.objects.create(
            report=report,
            student=student,
            reason=reason,
        )

    def get_extension_by_id(self, extension_id: int):
        return DeadlineExtensionRequest.objects.select_related('report', 'student').filter(pk=extension_id).first()

    def get_pending_extensions(self) -> QuerySet:
        return DeadlineExtensionRequest.objects.filter(
            status=DeadlineExtensionRequest.Status.PENDING,
        ).select_related('report', 'student')

    def resolve_extension(self, extension, *, status: str, reviewed_by, admin_note: str = ''):
        extension.status = status
        extension.reviewed_by = reviewed_by
        extension.admin_note = admin_note[:500]
        extension.resolved_at = timezone.now()
        extension.save()
        if status == DeadlineExtensionRequest.Status.APPROVED:
            settings_obj = SystemSettings.get_settings()
            settings_obj.submission_deadline = settings_obj.submission_deadline + timedelta(days=7)
            settings_obj.save(update_fields=['submission_deadline'])
        return extension

    def get_default_rubric(self):
        return Rubric.objects.filter(is_default=True, is_active=True).first()

    def get_project_group(self, group_id: int):
        return ProjectGroup.objects.filter(pk=group_id).first()

    def get_system_settings(self):
        return SystemSettings.get_settings()

    def update_system_settings(self, data: dict[str, Any]):
        settings_obj = SystemSettings.get_settings()
        for key, value in data.items():
            setattr(settings_obj, key, value)
        settings_obj.save()
        return settings_obj

    def get_rubric_rows(self, report) -> list[dict[str, Any]]:
        if not report.rubric_id:
            return []
        scores = report.rubric_scores_json or {}
        rows = []
        for c in report.rubric.iter_criteria():
            rows.append(
                {
                    'criterion_id': c.pk,
                    'criterion_name': c.name,
                    'score': int(scores.get(str(c.pk), scores.get(c.pk, 0))),
                    'max_score': c.max_score,
                }
            )
        return rows

    def bulk_eligible_for_admin_approve(self, report_ids: list[int]) -> QuerySet:
        return self.model_class.objects.filter(
            pk__in=report_ids,
            teacher_approved=True,
            status=Report.Status.PENDING,
            admin_approved=False,
            is_deleted=False,
        )

    def get_reports_by_ids(self, report_ids: list[int]) -> QuerySet:
        return self.model_class.objects.filter(pk__in=report_ids)

    def get_leaderboard_queryset(self, user, *, dept: str = '') -> QuerySet:
        qs = self.model_class.objects.filter(
            status=Report.Status.APPROVED,
            is_deleted=False,
            marks__isnull=False,
        ).select_related('student')
        role = getattr(user, 'role', None)
        if role == User.Role.TEACHER:
            from apps.reports.teacher_helpers import reports_for_teacher_q

            qs = qs.filter(reports_for_teacher_q(user))
        elif role == User.Role.STUDENT:
            student_dept = (user.department or '').strip()
            if student_dept:
                qs = qs.filter(student__department__iexact=student_dept)
            else:
                qs = qs.filter(student=user)
        if dept:
            qs = qs.filter(student__department__icontains=dept)
        return qs.order_by('-marks')

    def _monthly_submissions_last_6_months(self):
        now = timezone.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for _ in range(5):
            if start.month == 1:
                start = start.replace(year=start.year - 1, month=12)
            else:
                start = start.replace(month=start.month - 1)

        qs = (
            self.model_class.objects.filter(submitted_at__gte=start, is_deleted=False)
            .annotate(month=TruncMonth('submitted_at'))
            .values('month')
            .annotate(total=Count('id'))
            .order_by('month')
        )
        by_month = {row['month'].strftime('%Y-%m'): row['total'] for row in qs if row['month']}

        labels, values = [], []
        cur = start
        end_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while cur <= end_month:
            key = cur.strftime('%Y-%m')
            labels.append(cur.strftime('%b %Y'))
            values.append(by_month.get(key, 0))
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return labels, values

    def _monthly_approved_pending(self):
        now = timezone.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for _ in range(5):
            if start.month == 1:
                start = start.replace(year=start.year - 1, month=12)
            else:
                start = start.replace(month=start.month - 1)

        qs = (
            self.model_class.objects.filter(submitted_at__gte=start, is_deleted=False)
            .annotate(month=TruncMonth('submitted_at'))
            .values('month')
            .annotate(
                approved=Count('id', filter=Q(status=Report.Status.APPROVED)),
                pending=Count('id', filter=Q(status=Report.Status.PENDING)),
            )
            .order_by('month')
        )
        by_month = {}
        for row in qs:
            if row['month']:
                key = row['month'].strftime('%Y-%m')
                by_month[key] = (row['approved'], row['pending'])

        labels, approved_vals, pending_vals = [], [], []
        cur = start
        end_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while cur <= end_month:
            key = cur.strftime('%Y-%m')
            labels.append(cur.strftime('%b %Y'))
            pair = by_month.get(key, (0, 0))
            approved_vals.append(pair[0])
            pending_vals.append(pair[1])
            if cur.month == 12:
                cur = cur.replace(year=cur.year + 1, month=1)
            else:
                cur = cur.replace(month=cur.month + 1)
        return labels, approved_vals, pending_vals

    def get_analytics_stats(self) -> dict[str, Any]:
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
        total_reports = self.model_class.objects.filter(is_deleted=False).count()
        pending_reports = self.model_class.objects.filter(
            status=Report.Status.PENDING, is_deleted=False
        ).count()
        approved_reports = self.model_class.objects.filter(
            status=Report.Status.APPROVED, is_deleted=False
        ).count()
        rejected_reports = self.model_class.objects.filter(
            status=Report.Status.REJECTED, is_deleted=False
        ).count()
        denom = total_reports or 1
        approval_rate_pct = round(100.0 * approved_reports / denom, 1)
        late_n = self.model_class.objects.filter(is_late_submission=True, is_deleted=False).count()
        late_pct = round(100.0 * late_n / denom, 1)
        chart_labels, chart_values = self._monthly_submissions_last_6_months()
        _, chart_approved, chart_pending = self._monthly_approved_pending()
        settings_obj = SystemSettings.get_settings()
        return {
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_reports': total_reports,
            'pending_reports': pending_reports,
            'approved_reports': approved_reports,
            'rejected_reports': rejected_reports,
            'approval_rate_pct': approval_rate_pct,
            'late_pct': late_pct,
            'chart_labels': chart_labels,
            'chart_submissions': chart_values,
            'chart_approved': chart_approved,
            'chart_pending': chart_pending,
            'submission_deadline': settings_obj.submission_deadline,
            'max_attempts': settings_obj.max_attempts,
            'max_file_size_mb': settings_obj.max_file_size_mb,
        }

    def get_submission_tracking(self) -> dict[str, Any]:
        students = list(User.objects.filter(role=User.Role.STUDENT, is_active=True))
        has_report = self.model_class.objects.filter(is_deleted=False).values('student_id').distinct()
        has_ids = {r['student_id'] for r in has_report}
        submitted = [s for s in students if s.id in has_ids]
        pending = [s for s in students if s.id not in has_ids]
        return {
            'submitted_count': len(submitted),
            'pending_count': len(pending),
            'submitted': [
                {'id': s.id, 'username': s.username, 'department': s.department or ''}
                for s in submitted
            ],
            'pending': [
                {'id': s.id, 'username': s.username, 'department': s.department or ''}
                for s in pending
            ],
        }

    def get_teacher_workload(self, teacher) -> dict[str, int]:
        from apps.reports.teacher_helpers import reports_for_teacher_q

        rq = self.model_class.objects.filter(reports_for_teacher_q(teacher), is_deleted=False)
        return {
            'total': rq.count(),
            'done': rq.filter(status=Report.Status.APPROVED).count(),
            'pending_review': rq.filter(status=Report.Status.PENDING, teacher_approved=False).count(),
            'awaiting_admin': rq.filter(
                teacher_approved=True,
                admin_approved=False,
                status=Report.Status.PENDING,
            ).count(),
        }

    def get_department_rankings(self) -> list[dict[str, Any]]:
        qs = (
            User.objects.filter(role=User.Role.STUDENT)
            .exclude(department='')
            .values('department')
            .annotate(
                avg_marks=Avg(
                    'reports__marks',
                    filter=Q(
                        reports__status=Report.Status.APPROVED,
                        reports__is_deleted=False,
                        reports__marks__isnull=False,
                    ),
                ),
                report_count=Count(
                    'reports',
                    filter=Q(
                        reports__status=Report.Status.APPROVED,
                        reports__is_deleted=False,
                    ),
                ),
            )
            .order_by('-avg_marks')
        )
        return [
            {
                'department': row['department'],
                'avg_marks': round(row['avg_marks'] or 0, 2),
                'report_count': row['report_count'],
            }
            for row in qs
        ]

    def get_top_students(self, limit: int = 20) -> list[dict[str, Any]]:
        ranked = (
            User.objects.filter(role=User.Role.STUDENT)
            .annotate(
                avg_marks=Avg(
                    'reports__marks',
                    filter=Q(
                        reports__status=Report.Status.APPROVED,
                        reports__is_deleted=False,
                        reports__marks__isnull=False,
                    ),
                )
            )
            .filter(avg_marks__isnull=False)
            .order_by('-avg_marks', 'username')[:limit]
        )
        return [
            {
                'id': u.id,
                'username': u.username,
                'full_name': u.get_full_name() or u.username,
                'department': u.department or '',
                'avg_marks': round(u.avg_marks, 2),
            }
            for u in ranked
        ]

    def group_has_active_report(self, group_id: int) -> bool:
        return self.model_class.objects.filter(group_id=group_id, is_deleted=False).exists()

    def student_in_group(self, group, user_id: int) -> bool:
        return group.members.filter(pk=user_id).exists()

    def build_certificate_bytes(self, report) -> bytes:
        from application.services.certificate_service import CertificateService

        return CertificateService(self).build_pdf_bytes(report)


class NotificationRepository(BaseRepository[Notification]):
    model_class = Notification

    def for_user(self, user) -> QuerySet:
        return (
            self.get_queryset()
            .filter(user=user, notification_type=Notification.NotificationType.ALERT)
            .order_by('-created_at')
        )

    def mark_read(self, notification_id: int, user) -> Notification | None:
        notification = self.for_user(user).filter(pk=notification_id).first()
        if notification is None:
            return None
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return notification

    def mark_all_read(self, user) -> int:
        return self.for_user(user).filter(is_read=False).update(is_read=True)

    def delete_for_user(self, notification_id: int, user) -> bool:
        deleted, _ = self.for_user(user).filter(pk=notification_id).delete()
        return deleted > 0


class ActivityLogRepository(BaseRepository):
    model_class = None

    def __init__(self, model_class=None):
        from apps.reports.infrastructure.models import ActivityLog

        super().__init__(model_class or ActivityLog)

    def for_admin(self) -> QuerySet:
        return self.get_queryset().select_related('user', 'report').order_by('-timestamp')

    def apply_filters(self, qs: QuerySet, params: dict[str, Any]) -> QuerySet:
        user_search_query = (params.get('user_search') or '').strip()
        action_filter = params.get('action') or ''
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        search_query = (params.get('search') or '').strip()

        if user_search_query:
            qs = qs.filter(user__username__icontains=user_search_query)
        if action_filter:
            qs = qs.filter(action=action_filter)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        if search_query:
            qs = qs.filter(detail__icontains=search_query)
        return qs
