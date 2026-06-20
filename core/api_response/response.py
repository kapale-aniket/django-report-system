from typing import Any

from rest_framework.response import Response


class APIResponse:
    """Standard JSON envelope for every API endpoint."""

    @staticmethod
    def build(
        *,
        success: bool,
        message: str,
        data: Any = None,
        errors: list | None = None,
        status_code: int = 200,
    ) -> Response:
        payload = {
            'success': success,
            'message': message,
            'data': data if data is not None else {},
            'errors': errors or [],
            'status_code': status_code,
        }
        return Response(payload, status=status_code)

    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str = 'Operation successful',
        status_code: int = 200,
    ) -> Response:
        return cls.build(success=True, message=message, data=data, status_code=status_code)

    @classmethod
    def error(
        cls,
        message: str = 'Operation failed',
        errors: list | None = None,
        status_code: int = 400,
        data: Any = None,
    ) -> Response:
        return cls.build(
            success=False,
            message=message,
            data=data,
            errors=errors or [message],
            status_code=status_code,
        )
