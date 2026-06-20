from django.urls import path

from api.v1.reports import views as api_views

app_name = 'reports_api'

urlpatterns = [
    # Reports — list & submit
    path('', api_views.ReportListAPIView.as_view(), name='report_list'),
    path('my/', api_views.StudentMyReportsAPIView.as_view(), name='my_reports'),
    path('submit/', api_views.ReportSubmitAPIView.as_view(), name='submit'),
    path('bulk-action/', api_views.BulkReportActionAPIView.as_view(), name='bulk_action'),
    # Leaderboard & analytics
    path('leaderboard/', api_views.LeaderboardAPIView.as_view(), name='leaderboard'),
    path('analytics/', api_views.AnalyticsAPIView.as_view(), name='analytics'),
    path('settings/', api_views.SystemSettingsAPIView.as_view(), name='settings'),
    # Admin utilities
    path('activity-log/', api_views.ActivityLogListAPIView.as_view(), name='activity_log'),
    path('submission-tracking/', api_views.SubmissionTrackingAPIView.as_view(), name='submission_tracking'),
    path('extensions/', api_views.ExtensionQueueAPIView.as_view(), name='extension_queue'),
    path('extensions/<int:pk>/resolve/', api_views.ExtensionResolveAPIView.as_view(), name='extension_resolve'),
    path('reeval/<int:reeval_pk>/resolve/', api_views.ReEvaluationResolveAPIView.as_view(), name='reeval_resolve'),
    # Teacher
    path('teacher/assigned/', api_views.TeacherAssignedReportsAPIView.as_view(), name='teacher_assigned'),
    path('teacher/workload/', api_views.TeacherWorkloadAPIView.as_view(), name='teacher_workload'),
    # Notifications
    path('notifications/', api_views.NotificationListAPIView.as_view(), name='notifications'),
    path(
        'notifications/mark-all-read/',
        api_views.NotificationMarkAllReadAPIView.as_view(),
        name='notifications_mark_all_read',
    ),
    path(
        'notifications/<int:pk>/read/',
        api_views.NotificationMarkReadAPIView.as_view(),
        name='notification_read',
    ),
    path(
        'notifications/<int:pk>/',
        api_views.NotificationDeleteAPIView.as_view(),
        name='notification_delete',
    ),
    # Report detail & actions (pk routes last)
    path('<int:pk>/', api_views.ReportDetailAPIView.as_view(), name='detail'),
    path('<int:pk>/resubmit/', api_views.ReportResubmitAPIView.as_view(), name='resubmit'),
    path('<int:pk>/delete/', api_views.ReportDeleteAPIView.as_view(), name='delete'),
    path('<int:pk>/restore/', api_views.ReportRestoreAPIView.as_view(), name='restore'),
    path('<int:pk>/versions/', api_views.ReportVersionListAPIView.as_view(), name='versions'),
    path('<int:pk>/comment/', api_views.ReportCommentAPIView.as_view(), name='comment'),
    path('<int:pk>/bookmark/', api_views.ReportBookmarkAPIView.as_view(), name='bookmark'),
    path('<int:pk>/pin/', api_views.ReportPinAPIView.as_view(), name='toggle_pin'),
    path('<int:pk>/certificate/', api_views.ReportCertificateAPIView.as_view(), name='certificate'),
    path('<int:pk>/teacher-approve/', api_views.TeacherApproveAPIView.as_view(), name='teacher_approve'),
    path('<int:pk>/teacher-reject/', api_views.TeacherRejectAPIView.as_view(), name='teacher_reject'),
    path('<int:pk>/admin-approve/', api_views.AdminApproveAPIView.as_view(), name='admin_approve'),
    path('<int:pk>/admin-reject/', api_views.AdminRejectAPIView.as_view(), name='admin_reject'),
    path('<int:pk>/assign-teacher/', api_views.ReportAssignTeacherAPIView.as_view(), name='assign_teacher'),
    path('<int:pk>/reeval/', api_views.ReEvaluationRequestAPIView.as_view(), name='reeval_request'),
    path('<int:pk>/extension/', api_views.ExtensionRequestAPIView.as_view(), name='extension_request'),
    path('<int:pk>/ai-suggestions/', api_views.ReportAISuggestionsAPIView.as_view(), name='ai_suggestions'),
    path('<int:pk>/ai-process/', api_views.ReportAIProcessAPIView.as_view(), name='ai_process'),
]
