from django.urls import path

from api.v1.certificates import views

app_name = 'certificates_api'

urlpatterns = [
    path('verify/', views.CertificateVerifyAPIView.as_view(), name='verify'),
]
