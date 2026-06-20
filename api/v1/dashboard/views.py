from core.permissions.roles import IsAdmin, IsAuthenticatedRole, IsStudent, IsTeacher
from api.base.base_api_view import BaseAPIView

from application.services.dashboard_service import DashboardService


class DashboardServiceMixin:
    service_class = DashboardService

    def get_dashboard_service(self) -> DashboardService:
        return self.service_class()


def _serialize_announcements(announcements):
    return [
        {
            'id': item.id,
            'title': item.title,
            'message': item.message,
            'target_role': item.target_role,
            'created_at': item.created_at,
        }
        for item in announcements
    ]


def _serialize_activity_logs(logs):
    return [
        {
            'id': log.id,
            'action': log.action,
            'detail': log.detail,
            'timestamp': log.timestamp,
            'user_id': log.user_id,
            'report_id': log.report_id,
        }
        for log in logs
    ]


def _serialize_reports(reports):
    return [
        {
            'id': report.id,
            'title': report.title,
            'status': report.status,
            'submitted_at': report.submitted_at,
            'marks': report.marks,
        }
        for report in reports
    ]


class AdminAnalyticsAPIView(DashboardServiceMixin, BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        payload = self.run_service(
            lambda: self.get_dashboard_service().admin_analytics(),
            action='dashboard.admin_analytics',
            user=request.user,
        )
        return self.success(
            data={
                'total_students': payload['total_students'],
                'total_teachers': payload['total_teachers'],
                'total_reports': payload['total_reports'],
                'pending_reports': payload['pending_reports'],
                'approved_reports': payload['approved_reports'],
                'rejected_reports': payload['rejected_reports'],
                'approval_rate_pct': payload['approval_rate_pct'],
                'late_pct': payload['late_pct'],
                'chart_labels': payload['chart_labels'],
                'chart_values': payload['chart_values'],
                'chart_approved': payload['chart_approved'],
                'chart_pending': payload['chart_pending'],
                'submission_deadline': payload['submission_deadline'],
                'recent_logs': _serialize_activity_logs(payload['recent_logs']),
                'announcements': _serialize_announcements(payload['announcements']),
            },
            message='Admin analytics retrieved successfully',
        )


class TeacherDashboardAPIView(DashboardServiceMixin, BaseAPIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        payload = self.run_service(
            lambda: self.get_dashboard_service().teacher_dashboard(request.user),
            action='dashboard.teacher_dashboard',
            user=request.user,
        )
        return self.success(
            data={
                'assigned_reports': payload['assigned_reports'],
                'pending_teacher': payload['pending_teacher'],
                'awaiting_admin': payload['awaiting_admin'],
                'rejected_all': payload['rejected_all'],
                'approved_all': payload['approved_all'],
                'chart_labels': payload['chart_labels'],
                'chart_values': payload['chart_values'],
                'chart_approved': payload['chart_approved'],
                'chart_pending': payload['chart_pending'],
                'announcements': _serialize_announcements(payload['announcements']),
            },
            message='Teacher dashboard retrieved successfully',
        )


class StudentDashboardAPIView(DashboardServiceMixin, BaseAPIView):
    permission_classes = [IsStudent]

    def get(self, request):
        payload = self.run_service(
            lambda: self.get_dashboard_service().student_dashboard(request.user),
            action='dashboard.student_dashboard',
            user=request.user,
        )
        return self.success(
            data={
                'recent_reports': _serialize_reports(payload['recent_reports']),
                'pending_count': payload['pending_count'],
                'approved_count': payload['approved_count'],
                'rejected_count': payload['rejected_count'],
                'total_reports': payload['total_reports'],
                'student_rank': payload['student_rank'],
                'total_students_ranked': payload['total_students_ranked'],
                'recently_viewed': _serialize_reports(payload['recently_viewed']),
                'announcements': _serialize_announcements(payload['announcements']),
            },
            message='Student dashboard retrieved successfully',
        )
