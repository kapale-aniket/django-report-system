from django.urls import path

from api.v1.project_groups import views as api_views

app_name = 'project_groups_api'

urlpatterns = [
    path('', api_views.ProjectGroupListAPIView.as_view(), name='list'),
    path('my/', api_views.ProjectGroupMyAPIView.as_view(), name='my'),
    path('submittable/', api_views.ProjectGroupSubmittableAPIView.as_view(), name='submittable'),
    path('admin/', api_views.ProjectGroupAdminListAPIView.as_view(), name='admin_list'),
    path('create/', api_views.ProjectGroupCreateAPIView.as_view(), name='create'),
    path('<int:pk>/', api_views.ProjectGroupDetailAPIView.as_view(), name='detail'),
    path('<int:pk>/assign-teacher/', api_views.ProjectGroupAssignTeacherAPIView.as_view(), name='assign_teacher'),
]
