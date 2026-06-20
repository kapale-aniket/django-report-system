import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler as drf_exception_handler

from core.api_response import APIResponse
from core.exceptions.base import AppError
from core.utils.user_messages import (
    GENERIC_ERROR,
    GENERIC_NOT_FOUND,
    GENERIC_PERMISSION,
    GENERIC_SAVE_ERROR,
    GENERIC_VALIDATION,
    GENERIC_AUTH,
)

logger = logging.getLogger('reportflow.api')


def custom_exception_handler(exc, context):
    """Map all exceptions to the standard API envelope."""
    response = drf_exception_handler(exc, context)

    if isinstance(exc, AppError):
        logger.warning('App error: %s', exc.message, extra={'view': context.get('view')})
        return APIResponse.error(message=exc.message, status_code=exc.status_code)

    if isinstance(exc, ValidationError):
        errors = exc.detail if isinstance(exc.detail, list) else [str(exc.detail)]
        return APIResponse.error(message=GENERIC_VALIDATION, errors=errors, status_code=400)

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return APIResponse.error(message=GENERIC_AUTH, status_code=401)

    if isinstance(exc, PermissionDenied):
        return APIResponse.error(message=GENERIC_PERMISSION, status_code=403)

    if isinstance(exc, ObjectDoesNotExist):
        return APIResponse.error(message=GENERIC_NOT_FOUND, status_code=404)

    if isinstance(exc, DatabaseError):
        logger.exception('Database error', exc_info=exc)
        return APIResponse.error(message=GENERIC_SAVE_ERROR, status_code=500)

    if response is not None:
        errors = response.data if isinstance(response.data, list) else [str(response.data)]
        return APIResponse.error(
            message="We couldn't complete that request. Please try again.",
            errors=errors,
            status_code=response.status_code,
        )

    logger.exception('Unexpected API error', exc_info=exc)
    return APIResponse.error(message=GENERIC_ERROR, status_code=500)
