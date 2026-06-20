from django.urls import path

from apps.reports import certificate_views

app_name = 'certificates'

urlpatterns = [
    path('verify/', certificate_views.verify_certificate_page, name='verify'),
]
