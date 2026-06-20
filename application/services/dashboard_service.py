from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.reports.infrastructure.models import (
    ActivityLog,
    Announcement,
    Report,
    ReportRecentView,
    SystemSettings,
)
from apps.reports.teacher_helpers import reports_for_teacher_q

User = get_user_model()


class DashboardService:
    """Aggregates dashboard statistics reused from legacy template views."""

    def _month_window_start(self):
        start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for _ in range(5):
            if start.month == 1:
                start = start.replace(year=start.year - 1, month=12)
            else:
                start = start.replace(month=start.month - 1)
        return start

    def _monthly_submissions_last_6_months(self):
        start = self._month_window_start()
        qs = (
            Report.objects.filter(submitted_at__gte=start, is_deleted=False)
            .annotate(month=TruncMonth('submitted_at'))
            .values('month')
            .annotate(total=Count('id'))
            .order_by('month')
        )
        by_month = {row['month'].strftime('%Y-%m'): row['total'] for row in qs if row['month']}

        labels = []
        values = []
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
        start = self._month_window_start()
        qs = (
            Report.objects.filter(submitted_at__gte=start, is_deleted=False)
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

        labels = []
        approved_vals = []
        pending_vals = []
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

    def _announcements_for_role(self, role: str):
        return list(
            Announcement.objects.filter(is_active=True)
            .filter(Q(target_role=Announcement.TargetRole.ALL) | Q(target_role=role))
            .order_by('-created_at')[:5]
        )

    def admin_analytics(self):
        settings_obj = SystemSettings.get_settings()
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
        total_reports = Report.objects.filter(is_deleted=False).count()
        pending_reports = Report.objects.filter(status=Report.Status.PENDING, is_deleted=False).count()
        approved_reports = Report.objects.filter(status=Report.Status.APPROVED, is_deleted=False).count()
        rejected_reports = Report.objects.filter(status=Report.Status.REJECTED, is_deleted=False).count()
        denom = total_reports or 1
        approval_rate_pct = round(100.0 * approved_reports / denom, 1)
        late_n = Report.objects.filter(is_late_submission=True, is_deleted=False).count()
        late_pct = round(100.0 * late_n / denom, 1)

        chart_labels, chart_values = self._monthly_submissions_last_6_months()
        _, chart_approved, chart_pending = self._monthly_approved_pending()
        recent_logs = list(ActivityLog.objects.select_related('user', 'report')[:25])

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
            'chart_values': chart_values,
            'chart_approved': chart_approved,
            'chart_pending': chart_pending,
            'submission_deadline': settings_obj.submission_deadline,
            'recent_logs': recent_logs,
            'announcements': self._announcements_for_role(User.Role.ADMIN),
        }

    def teacher_dashboard(self, teacher):
        rq = Report.objects.filter(reports_for_teacher_q(teacher), is_deleted=False)
        all_reports = rq.count()
        pending_teacher = rq.filter(
            status=Report.Status.PENDING,
            teacher_approved=False,
        ).count()
        awaiting_admin = rq.filter(
            teacher_approved=True,
            admin_approved=False,
            status=Report.Status.PENDING,
        ).count()
        rejected_all = rq.filter(status=Report.Status.REJECTED).count()
        approved_all = rq.filter(status=Report.Status.APPROVED).count()

        chart_labels, chart_values = self._monthly_submissions_last_6_months()
        _, chart_approved, chart_pending = self._monthly_approved_pending()

        return {
            'assigned_reports': all_reports,
            'pending_teacher': pending_teacher,
            'awaiting_admin': awaiting_admin,
            'rejected_all': rejected_all,
            'approved_all': approved_all,
            'chart_labels': chart_labels,
            'chart_values': chart_values,
            'chart_approved': chart_approved,
            'chart_pending': chart_pending,
            'announcements': self._announcements_for_role(User.Role.TEACHER),
        }

    def student_dashboard(self, student):
        base = Report.objects.filter(student=student, is_deleted=False)
        recent = list(base.order_by('-submitted_at')[:5])
        pending = base.filter(status=Report.Status.PENDING).count()
        approved = base.filter(status=Report.Status.APPROVED).count()
        rejected = base.filter(status=Report.Status.REJECTED).count()
        total_reports = base.count()

        ranked = list(
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
            .order_by('-avg_marks', 'username')
        )
        total_students_ranked = len(ranked)
        student_rank = None
        for index, user in enumerate(ranked, start=1):
            if user.id == student.id:
                student_rank = index
                break
        if student_rank is None:
            student_rank = None

        recently_viewed = [
            rv.report
            for rv in ReportRecentView.objects.filter(user=student).select_related('report')[:8]
            if not rv.report.is_deleted
        ]

        return {
            'recent_reports': recent,
            'pending_count': pending,
            'approved_count': approved,
            'rejected_count': rejected,
            'total_reports': total_reports,
            'student_rank': student_rank,
            'total_students_ranked': total_students_ranked,
            'recently_viewed': recently_viewed,
            'announcements': self._announcements_for_role(User.Role.STUDENT),
        }
