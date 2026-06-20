"""Backward-compatible re-exports — use api.v1.auth.views in new code."""
from api.v1.auth.views import (  # noqa: F401
    AssignTeacherAPIView,
    ChangePasswordAPIView,
    CreateUserAPIView,
    ForgotPasswordAPIView,
    LoginAPIView,
    LogoutAPIView,
    PendingStudentsAPIView,
    ProfileAPIView,
    RegisterStudentAPIView,
    RegisterTeacherAPIView,
    ResetPasswordAPIView,
    UserApproveAPIView,
    UserDeleteAPIView,
    UserListAPIView,
)

__all__ = [
    'LoginAPIView',
    'LogoutAPIView',
    'RegisterStudentAPIView',
    'RegisterTeacherAPIView',
    'ProfileAPIView',
    'ChangePasswordAPIView',
    'ForgotPasswordAPIView',
    'ResetPasswordAPIView',
    'UserListAPIView',
    'UserApproveAPIView',
    'UserDeleteAPIView',
    'AssignTeacherAPIView',
    'PendingStudentsAPIView',
    'CreateUserAPIView',
]
