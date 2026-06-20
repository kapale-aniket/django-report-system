"""
Master API router at /api/v1/

All modules routed through api/v1/* (Steps 3–5 complete).
"""
from django.urls import include, path

urlpatterns = [
    path('', include('api.v1.auth.urls')),
    path('reports/', include('api.v1.reports.urls')),
    path('project-groups/', include('api.v1.project_groups.urls')),
    path('messages/', include('api.v1.messaging.urls')),
    path('qa/', include('api.v1.qa.urls')),
    path('dashboard/', include('api.v1.dashboard.urls')),
    path('certificates/', include('api.v1.certificates.urls')),
]
