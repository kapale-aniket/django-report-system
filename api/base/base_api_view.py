"""
Enterprise API view base.

Bridge: re-exports core implementation until api/ fully owns presentation helpers.
"""
from core.presentation.base_api_view import BaseAPIView

__all__ = ['BaseAPIView']
