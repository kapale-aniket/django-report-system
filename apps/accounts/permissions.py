"""
Role-based permission helpers (no third-party packages).
Use with decorators below or call from views.
"""
from functools import wraps

from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from .models import User


def user_can_approve_reports(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.role in (User.Role.TEACHER, User.Role.ADMIN)


def user_can_final_approve(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def user_can_assign_teacher(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def user_can_manage_users(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def user_can_pin_reports(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def user_can_review_extension(user) -> bool:
    return user.is_authenticated and user.role == User.Role.ADMIN


def approval_required(view_func):
    """Teacher or Admin only."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not user_can_approve_reports(request.user):
            return redirect('accounts:post_login_redirect')
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_only(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if request.user.role != User.Role.ADMIN:
            return redirect('accounts:post_login_redirect')
        return view_func(request, *args, **kwargs)

    return _wrapped
