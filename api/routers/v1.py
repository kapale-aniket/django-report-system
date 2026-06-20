"""
Future v1 router aggregator.

When migration completes, api/urls.py will use:
    path('v1/', include('api.routers.v1'))
"""
from django.urls import include, path

urlpatterns = [
    # path('auth/', include('api.v1.auth.urls')),
    # path('reports/', include('api.v1.reports.urls')),
]
