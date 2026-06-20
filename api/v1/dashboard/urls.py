from django.urls import path

from api.v1.dashboard import views as api_views

app_name = 'dashboard_api'

urlpatterns = [
    path('admin/', api_views.AdminAnalyticsAPIView.as_view(), name='admin_analytics'),
    path('teacher/', api_views.TeacherDashboardAPIView.as_view(), name='teacher_dashboard'),
    path('student/', api_views.StudentDashboardAPIView.as_view(), name='student_dashboard'),
]
