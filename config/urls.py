from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'login/',
        RedirectView.as_view(pattern_name='accounts:login', permanent=False),
        name='login_alias',
    ),
    # Template (legacy) routes
    path('accounts/', include('apps.accounts.urls')),
    path('reports/', include('apps.reports.urls')),
    path('certificates/', include('apps.reports.certificate_urls')),
    path('messages/', include('apps.messaging.urls')),
    path('qa/', include('apps.qa.urls')),
    path('', include('apps.dashboard.urls')),
    # Enterprise API
    path('api/v1/', include('api.urls')),
    # OpenAPI / Swagger
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
