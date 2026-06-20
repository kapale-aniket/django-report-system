from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView

from . import views
from .forms import BootstrapPasswordResetForm, BootstrapSetPasswordForm

app_name = 'accounts'

urlpatterns = [
    path('login/', views.AppLoginView.as_view(), name='login'),
    path(
        'login/<str:role>/',
        RedirectView.as_view(pattern_name='accounts:login', permanent=False),
        name='login_role',
    ),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            form_class=BootstrapPasswordResetForm,
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/password_reset_email.txt',
            subject_template_name='accounts/password_reset_subject.txt',
            success_url=reverse_lazy('accounts:password_reset_done'),
            extra_email_context={'site_name': 'ReportFlow'},
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            form_class=BootstrapSetPasswordForm,
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('accounts:password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('logout/', views.logout_view, name='logout'),
    path('session-check/', views.session_check, name='session_check'),
    path('redirect/', views.post_login_redirect, name='post_login_redirect'),
    path('register/student/', views.register_student, name='register_student'),
    path('register/teacher/', views.register_teacher, name='register_teacher'),
    path('register/', views.register_hub, name='register_hub'),
    path('pending-students/', views.pending_students, name='pending_students'),
    path('pending-students/<int:pk>/approve/', views.approve_student, name='approve_student'),
    path('users/', views.user_list_create, name='user_management'),
    path('users/<int:pk>/approve/', views.approve_user, name='approve_user'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('users/<int:pk>/update/', views.user_update, name='user_update'),
    path('users/<int:pk>/set-active/', views.user_set_active, name='user_set_active'),
    path('users/<int:pk>/assign-teacher/', views.assign_teacher, name='assign_teacher'),
]
