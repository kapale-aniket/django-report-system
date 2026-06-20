"""Backward-compatible re-exports — use application.services directly in new code."""
from application.services.auth_service import AuthService
from application.services.user_management_service import UserManagementService

__all__ = ['AuthService', 'UserManagementService']
