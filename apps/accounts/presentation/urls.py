"""Backward-compatible — routes now served from api.v1.auth.urls via api/urls.py."""
from api.v1.auth.urls import app_name, urlpatterns

__all__ = ['urlpatterns', 'app_name']
