import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.views import APIView

from core.api_response import APIResponse
from core.exceptions.base import AppError
from core.exceptions.handler import custom_exception_handler
from core.utils.user_messages import GENERIC_ERROR
from core.mixins.logging import AuditLogMixin
from core.pagination import StandardPagination
from core.utils.logger import log_api_error

logger = logging.getLogger('reportflow.api')


class BaseAPIView(AuditLogMixin, APIView):
    """
    Enterprise API base:
    - Standard response envelope
    - Central exception handling
    - Audit logging hooks
    - Pagination / filter backends for list views
    """

    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields: list[str] = []
    search_fields: list[str] = []
    ordering_fields: list[str] = []
    ordering: list[str] = ['-id']

    def get_exception_handler(self):
        return custom_exception_handler

    def handle_exception(self, exc):
        handler = self.get_exception_handler()
        response = handler(exc, {'view': self, 'request': getattr(self, 'request', None)})
        if response is not None:
            return response
        log_api_error(logger, 'Unhandled exception in API view', exc)
        return APIResponse.error(message=GENERIC_ERROR, status_code=500)

    def success(self, data=None, message='Operation successful', status_code=status.HTTP_200_OK):
        return APIResponse.success(data=data, message=message, status_code=status_code)

    def error(self, message='Operation failed', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return APIResponse.error(message=message, errors=errors, status_code=status_code)

    def paginate_queryset(self, queryset):
        if self.pagination_class is None:
            return None
        self.paginator = self.pagination_class()
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        paginator = getattr(self, 'paginator', None)
        if paginator is None:
            return self.success(data=data, message='List retrieved successfully')
        return paginator.get_paginated_response(data)

    def run_service(self, callback, *, action: str = '', user=None):
        """Execute service call with AppError translation."""
        try:
            return callback()
        except AppError:
            raise
        except Exception as exc:
            log_api_error(logger, f'Service error during {action}', exc)
            raise AppError(GENERIC_ERROR) from exc
