from __future__ import annotations

import io

from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated

from application.services.report_service import NotificationService, ReportService
from api.filters.reports import ReportFilterSet
from api.serializers.reports import (
    ActivityLogSerializer,
    AdminApproveSerializer,
    AnalyticsSerializer,
    BulkActionSerializer,
    CommentCreateSerializer,
    CommentSerializer,
    DepartmentRankingSerializer,
    ExtensionCreateSerializer,
    ExtensionResolveSerializer,
    ExtensionRequestSerializer,
    LeaderboardReportSerializer,
    NotificationSerializer,
    ReEvaluationCreateSerializer,
    ReEvaluationResolveSerializer,
    ReEvaluationRequestSerializer,
    RejectSerializer,
    ReportAssignTeacherSerializer,
    ReportDetailSerializer,
    ReportListSerializer,
    ReportResubmitSerializer,
    ReportSubmitSerializer,
    ReportVersionSerializer,
    SubmissionTrackingSerializer,
    SystemSettingsSerializer,
    TeacherApproveSerializer,
    TeacherWorkloadSerializer,
    TopStudentSerializer,
)
from core.permissions import IsAdmin, IsAuthenticatedRole, IsStudent, IsTeacher
from api.base.base_api_view import BaseAPIView
from application.services.ai_report_service import AIReportService
from api.serializers.ai import ReportAISuggestionsSerializer


def _report_service() -> ReportService:
    return ReportService()


def _notification_service() -> NotificationService:
    return NotificationService()


def _coerce_request_dict(raw_data) -> dict:
    if hasattr(raw_data, 'dict'):
        return raw_data.dict()
    if hasattr(raw_data, 'items'):
        return {key: raw_data.get(key) for key in raw_data.keys()}
    return dict(raw_data)


def _normalize_teacher_approve_data(raw_data) -> dict:
    data = _coerce_request_dict(raw_data)
    scores = data.get('criterion_scores') or {}
    if not scores:
        for key in list(data.keys()):
            if key.startswith('criterion_'):
                criterion_id = key[len('criterion_'):]
                try:
                    scores[criterion_id] = int(data.pop(key))
                except (TypeError, ValueError):
                    scores[criterion_id] = 0
        if scores:
            data['criterion_scores'] = scores

    if 'is_final_submission' in data:
        checkbox_value = data['is_final_submission']
        data['is_final_submission'] = checkbox_value in ('on', 'true', 'True', '1', 1, True)

    teacher_marks = data.get('teacher_marks')
    if teacher_marks in ('', None):
        data['teacher_marks'] = None
    elif teacher_marks is not None:
        try:
            data['teacher_marks'] = int(teacher_marks)
        except (TypeError, ValueError):
            pass

    return data


def _normalize_reeval_resolve_data(raw_data) -> dict:
    data = _coerce_request_dict(raw_data)
    if 'action' not in data and 'resolve_action' in data:
        data['action'] = data.pop('resolve_action')
    updated_marks = data.get('updated_marks')
    if updated_marks not in ('', None):
        try:
            data['updated_marks'] = int(updated_marks)
        except (TypeError, ValueError):
            pass
    return data


def _filter_queryset(view, queryset):
    for backend in view.filter_backends:
        queryset = backend().filter_queryset(view.request, queryset, view)
    return queryset


class ReportListAPIView(BaseAPIView):
    """Role-scoped report list with search, filter, ordering, pagination."""

    permission_classes = [IsAuthenticatedRole]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ReportFilterSet
    search_fields = ['title', 'student__username', 'student__first_name', 'student__last_name', 'tags']
    ordering_fields = ['submitted_at', 'marks', 'title', 'updated_at', 'is_pinned']
    ordering = ['-is_pinned', '-submitted_at']

    def get(self, request):
        service = _report_service()
        queryset = self.run_service(
            lambda: service.get_list_queryset(request.user),
            action='list_reports',
            user=request.user,
        )
        queryset = _filter_queryset(self, queryset)
        page = self.paginate_queryset(queryset)
        serializer = ReportListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class StudentMyReportsAPIView(ReportListAPIView):
    """Student-only alias for my reports."""

    permission_classes = [IsStudent]


class ReportSubmitAPIView(BaseAPIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = ReportSubmitSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data.copy()
        if request.FILES.get('file'):
            data['file'] = request.FILES['file']
        service = _report_service()
        report = self.run_service(
            lambda: service.submit_report(request.user, data),
            action='submit_report',
            user=request.user,
        )
        return self.success(
            data=ReportListSerializer(report).data,
            message='Report submitted successfully',
            status_code=status.HTTP_201_CREATED,
        )


class ReportDetailAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request, pk):
        service = _report_service()
        detail = self.run_service(
            lambda: service.get_detail(request.user, pk),
            action='get_detail',
            user=request.user,
        )
        report = detail['report']
        payload = ReportDetailSerializer(report).data
        payload.update(
            {
                'bookmarked': detail['bookmarked'],
                'can_comment': detail['can_comment'],
                'can_resubmit': detail['can_resubmit'],
                'rubric_rows': detail['rubric_rows'],
                'pending_reeval': (
                    ReEvaluationRequestSerializer(detail['pending_reeval']).data
                    if detail['pending_reeval']
                    else None
                ),
                'pending_extension': (
                    ExtensionRequestSerializer(detail['pending_extension']).data
                    if detail['pending_extension']
                    else None
                ),
                'reeval_admin_queue': ReEvaluationRequestSerializer(
                    detail['reeval_admin_queue'], many=True
                ).data,
                'versions': ReportVersionSerializer(detail['versions'], many=True).data,
                'timeline': ActivityLogSerializer(detail['timeline'], many=True).data,
                'settings': SystemSettingsSerializer(detail['settings']).data,
                'report_max_attempts': detail.get('report_max_attempts'),
            }
        )
        return self.success(data=payload, message='Report retrieved successfully')


class ReportResubmitAPIView(BaseAPIView):
    permission_classes = [IsStudent]

    def post(self, request, pk):
        serializer = ReportResubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uploaded = request.FILES.get('file') or serializer.validated_data['file']
        service = _report_service()
        report = self.run_service(
            lambda: service.resubmit_report(request.user, pk, uploaded),
            action='resubmit_report',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Report resubmitted successfully')


class ReportDeleteAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request, pk):
        service = _report_service()
        report = self.run_service(
            lambda: service.delete_report(request.user, pk),
            action='delete_report',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Report moved to trash')

    def delete(self, request, pk):
        return self.post(request, pk)


class ReportRestoreAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        service = _report_service()
        report = self.run_service(
            lambda: service.restore_report(request.user, pk),
            action='restore_report',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Report restored')


class ReportVersionListAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request, pk):
        service = _report_service()
        versions = self.run_service(
            lambda: service.get_versions(request.user, pk),
            action='get_versions',
            user=request.user,
        )
        return self.success(
            data=ReportVersionSerializer(versions, many=True).data,
            message='Version history retrieved',
        )


class ReportCommentAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request, pk):
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        comment = self.run_service(
            lambda: service.add_comment(
                request.user, pk, serializer.validated_data['message']
            ),
            action='add_comment',
            user=request.user,
        )
        return self.success(
            data=CommentSerializer(comment).data,
            message='Comment posted',
            status_code=status.HTTP_201_CREATED,
        )


class ReportBookmarkAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request, pk):
        service = _report_service()
        bookmarked = self.run_service(
            lambda: service.toggle_bookmark(request.user, pk),
            action='toggle_bookmark',
            user=request.user,
        )
        return self.success(
            data={'bookmarked': bookmarked},
            message='Bookmarked' if bookmarked else 'Bookmark removed',
        )


class ReportPinAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        service = _report_service()
        report = self.run_service(
            lambda: service.toggle_pin(request.user, pk),
            action='toggle_pin',
            user=request.user,
        )
        return self.success(
            data={'is_pinned': report.is_pinned},
            message='Pinned state updated',
        )


class ReportCertificateAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request, pk):
        service = _report_service()
        pdf_bytes = self.run_service(
            lambda: service.get_certificate_bytes(request.user, pk),
            action='download_certificate',
            user=request.user,
        )
        return FileResponse(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            filename=f'report_{pk}_certificate.pdf',
            content_type='application/pdf',
        )


class TeacherApproveAPIView(BaseAPIView):
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        payload = _normalize_teacher_approve_data(request.data)
        serializer = TeacherApproveSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        report = self.run_service(
            lambda: service.teacher_approve(request.user, pk, serializer.validated_data),
            action='teacher_approve',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Teacher approval saved')


class TeacherRejectAPIView(BaseAPIView):
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        report = self.run_service(
            lambda: service.teacher_reject(
                request.user, pk, serializer.validated_data['reason']
            ),
            action='teacher_reject',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Report rejected')


class AdminApproveAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        serializer = AdminApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        report = self.run_service(
            lambda: service.admin_approve(
                request.user, pk, serializer.validated_data['marks']
            ),
            action='admin_approve',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Final approval saved')


class AdminRejectAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        report = self.run_service(
            lambda: service.admin_reject(
                request.user, pk, serializer.validated_data['reason']
            ),
            action='admin_reject',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Report rejected')


class ReportAssignTeacherAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        serializer = ReportAssignTeacherSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        report = self.run_service(
            lambda: service.assign_report_teacher(
                request.user,
                pk,
                serializer.validated_data.get('teacher_id'),
            ),
            action='assign_report_teacher',
            user=request.user,
        )
        return self.success(data=ReportListSerializer(report).data, message='Project teacher updated')


class BulkReportActionAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        result = self.run_service(
            lambda: service.bulk_admin_approve_or_reject(
                request.user,
                serializer.validated_data['report_ids'],
                serializer.validated_data['action'],
                serializer.validated_data.get('reason', ''),
            ),
            action='bulk_action',
            user=request.user,
        )
        return self.success(data=result, message='Bulk action completed')


class ReEvaluationRequestAPIView(BaseAPIView):
    permission_classes = [IsStudent]

    def post(self, request, pk):
        serializer = ReEvaluationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        reevaluation_request = self.run_service(
            lambda: service.request_reevaluation(
                request.user, pk, serializer.validated_data['reason']
            ),
            action='request_reevaluation',
            user=request.user,
        )
        return self.success(
            data=ReEvaluationRequestSerializer(reevaluation_request).data,
            message='Re-evaluation request submitted',
            status_code=status.HTTP_201_CREATED,
        )


class ReEvaluationResolveAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, reeval_pk):
        payload = _normalize_reeval_resolve_data(request.data)
        serializer = ReEvaluationResolveSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        reevaluation_request = self.run_service(
            lambda: service.resolve_reevaluation(
                request.user,
                reeval_pk,
                serializer.validated_data['action'],
                serializer.validated_data.get('updated_marks'),
            ),
            action='resolve_reevaluation',
            user=request.user,
        )
        return self.success(
            data=ReEvaluationRequestSerializer(reevaluation_request).data,
            message='Re-evaluation resolved',
        )


class ExtensionRequestAPIView(BaseAPIView):
    permission_classes = [IsStudent]

    def post(self, request, pk):
        serializer = ExtensionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        extension_request = self.run_service(
            lambda: service.request_extension(
                request.user, pk, serializer.validated_data['reason']
            ),
            action='request_extension',
            user=request.user,
        )
        return self.success(
            data=ExtensionRequestSerializer(extension_request).data,
            message='Extension request submitted',
            status_code=status.HTTP_201_CREATED,
        )


class ExtensionQueueAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        service = _report_service()
        extensions = self.run_service(
            lambda: service.get_extension_queue(request.user),
            action='extension_queue',
            user=request.user,
        )
        return self.success(
            data=ExtensionRequestSerializer(extensions, many=True).data,
            message='Extension queue retrieved',
        )


class ExtensionResolveAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        serializer = ExtensionResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        extension_request = self.run_service(
            lambda: service.resolve_extension(
                request.user,
                pk,
                serializer.validated_data['decision'],
                serializer.validated_data.get('note', ''),
            ),
            action='resolve_extension',
            user=request.user,
        )
        return self.success(
            data=ExtensionRequestSerializer(extension_request).data,
            message='Extension request resolved',
        )


class TeacherWorkloadAPIView(BaseAPIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        service = _report_service()
        stats = self.run_service(
            lambda: service.get_teacher_workload(request.user),
            action='teacher_workload',
            user=request.user,
        )
        return self.success(
            data=TeacherWorkloadSerializer(stats).data,
            message='Teacher workload retrieved',
        )


class TeacherAssignedReportsAPIView(ReportListAPIView):
    """Teacher assigned reports list."""

    permission_classes = [IsTeacher]


class ActivityLogListAPIView(BaseAPIView):
    permission_classes = [IsAdmin]
    pagination_class = BaseAPIView.pagination_class

    def get(self, request):
        params = {
            'user_search': request.query_params.get('user_search', ''),
            'action': request.query_params.get('action', ''),
            'date_from': request.query_params.get('date_from'),
            'date_to': request.query_params.get('date_to'),
            'search': request.query_params.get('search', ''),
        }
        service = _report_service()
        queryset = self.run_service(
            lambda: service.get_activity_logs(request.user, params),
            action='activity_logs',
            user=request.user,
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(ActivityLogSerializer(page, many=True).data)


class SubmissionTrackingAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        service = _report_service()
        data = self.run_service(
            lambda: service.get_submission_tracking(request.user),
            action='submission_tracking',
            user=request.user,
        )
        return self.success(
            data=SubmissionTrackingSerializer(data).data,
            message='Submission tracking retrieved',
        )


class LeaderboardAPIView(BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request):
        dept = request.query_params.get('dept', '').strip()
        service = _report_service()
        data = self.run_service(
            lambda: service.get_leaderboard(request.user, dept=dept),
            action='leaderboard',
            user=request.user,
        )
        return self.success(
            data={
                'top_reports': LeaderboardReportSerializer(data['top_reports'], many=True).data,
                'top_students': TopStudentSerializer(data['top_students'], many=True).data,
                'department_rankings': DepartmentRankingSerializer(
                    data['department_rankings'], many=True
                ).data,
                'dept_filter': data['dept_filter'],
            },
            message='Leaderboard retrieved',
        )


class AnalyticsAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        service = _report_service()
        stats = self.run_service(
            lambda: service.get_analytics(request.user),
            action='analytics',
            user=request.user,
        )
        return self.success(
            data=AnalyticsSerializer(stats).data,
            message='Analytics retrieved',
        )


class SystemSettingsAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        service = _report_service()
        settings_obj = self.run_service(
            lambda: service.get_system_settings(request.user),
            action='get_system_settings',
            user=request.user,
        )
        return self.success(
            data=SystemSettingsSerializer(settings_obj).data,
            message='System settings retrieved',
        )

    def put(self, request):
        serializer = SystemSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        service = _report_service()
        settings_obj = self.run_service(
            lambda: service.update_system_settings(
                request.user, serializer.validated_data
            ),
            action='update_system_settings',
            user=request.user,
        )
        return self.success(
            data=SystemSettingsSerializer(settings_obj).data,
            message='System settings updated',
        )

    def patch(self, request):
        return self.put(request)


class NotificationListAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = _notification_service()
        queryset = self.run_service(
            lambda: service.list_notifications(request.user),
            action='list_notifications',
            user=request.user,
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(NotificationSerializer(page, many=True).data)


class NotificationMarkReadAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        service = _notification_service()
        notification = self.run_service(
            lambda: service.mark_read(request.user, pk),
            action='mark_read',
            user=request.user,
        )
        return self.success(
            data={
                **NotificationSerializer(notification).data,
                'redirect_url': (notification.link or '').strip() or None,
            },
            message='Notification marked read',
        )


class NotificationMarkAllReadAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        service = _notification_service()
        count = self.run_service(
            lambda: service.mark_all_read(request.user),
            action='mark_all_read',
            user=request.user,
        )
        return self.success(data={'updated': count}, message='All notifications marked read')


class NotificationDeleteAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        service = _notification_service()
        self.run_service(
            lambda: service.delete_notification(request.user, pk),
            action='delete_notification',
            user=request.user,
        )
        return self.success(message='Notification deleted')


class ReportAISuggestionsAPIView(BaseAPIView):
    """AI summary, OCR verification, and rubric score suggestions for teachers."""

    permission_classes = [IsAuthenticatedRole]

    def get(self, request, pk):
        service = AIReportService()
        payload = self.run_service(
            lambda: service.get_teacher_insights(request.user, pk),
            action='report.ai_suggestions',
            user=request.user,
        )
        serializer = ReportAISuggestionsSerializer(payload)
        return self.success(data=serializer.data, message='AI insights retrieved')


class ReportAIProcessAPIView(BaseAPIView):
    """Re-run PDF extraction, OCR verification, and AI analysis."""

    permission_classes = [IsAuthenticatedRole]

    def post(self, request, pk):
        from tasks.dispatch import queue_report_ai_analysis
        from apps.reports.infrastructure.models import Report

        report_service = _report_service()
        report = report_service._get_report_or_404(pk)
        report_service._ensure_view_access(request.user, report)
        role = getattr(request.user, 'role', None)
        if role not in ('teacher', 'admin'):
            from core.exceptions.base import PermissionAppError
            raise PermissionAppError('Only teachers and admins can run AI analysis.')
        report.ai_processing_status = Report.AIProcessingStatus.PENDING
        report.save(update_fields=['ai_processing_status'])
        queue_report_ai_analysis(pk)
        return self.success(message='AI analysis queued')
