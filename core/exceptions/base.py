from core.utils.user_messages import (
    GENERIC_AUTH,
    GENERIC_BUSINESS,
    GENERIC_ERROR,
    GENERIC_NOT_FOUND,
    GENERIC_PERMISSION,
    GENERIC_VALIDATION,
)


class AppError(Exception):
    """Base application exception."""

    default_message = GENERIC_ERROR
    status_code = 400

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class ValidationAppError(AppError):
    default_message = GENERIC_VALIDATION
    status_code = 400


class AuthenticationAppError(AppError):
    default_message = GENERIC_AUTH
    status_code = 401


class PermissionAppError(AppError):
    default_message = GENERIC_PERMISSION
    status_code = 403


class NotFoundAppError(AppError):
    default_message = GENERIC_NOT_FOUND
    status_code = 404


class BusinessLogicError(AppError):
    default_message = GENERIC_BUSINESS
    status_code = 422
