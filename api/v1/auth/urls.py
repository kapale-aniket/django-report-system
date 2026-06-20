from django.urls import path

from api.v1.auth import views

app_name = 'accounts_api'

urlpatterns = [
    path('auth/login/', views.LoginAPIView.as_view(), name='login'),
    path('auth/logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('auth/register/student/', views.RegisterStudentAPIView.as_view(), name='register_student'),
    path('auth/register/teacher/', views.RegisterTeacherAPIView.as_view(), name='register_teacher'),
    path('auth/profile/', views.ProfileAPIView.as_view(), name='profile'),
    path('auth/profile/photo/', views.ProfilePhotoAPIView.as_view(), name='profile_photo'),
    path('auth/change-password/', views.ChangePasswordAPIView.as_view(), name='change_password'),
    path('auth/forgot-password/', views.ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('auth/reset-password/', views.ResetPasswordAPIView.as_view(), name='reset_password'),
    path('users/', views.UserListAPIView.as_view(), name='user_list'),
    path('users/create/', views.CreateUserAPIView.as_view(), name='user_create'),
    path('users/pending-students/', views.PendingStudentsAPIView.as_view(), name='pending_students'),
    path('users/<int:pk>/approve/', views.UserApproveAPIView.as_view(), name='user_approve'),
    path('users/<int:pk>/delete/', views.UserDeleteAPIView.as_view(), name='user_delete'),
    path('users/<int:pk>/update/', views.UserUpdateAPIView.as_view(), name='user_update'),
    path('users/<int:pk>/set-active/', views.UserSetActiveAPIView.as_view(), name='user_set_active'),
    path('users/<int:pk>/assign-teacher/', views.AssignTeacherAPIView.as_view(), name='assign_teacher'),
    path('users/<int:pk>/students/', views.TeacherStudentsAPIView.as_view(), name='teacher_students'),
    path('teachers/', views.TeachersByDepartmentAPIView.as_view(), name='teachers_by_department'),
    path('departments/', views.DepartmentListCreateAPIView.as_view(), name='departments'),
]
