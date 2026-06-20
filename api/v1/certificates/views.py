"""Certificate verification API."""
from rest_framework.permissions import AllowAny

from api.base.base_api_view import BaseAPIView
from application.services.certificate_service import CertificateService


def _certificate_service() -> CertificateService:
    return CertificateService()


class CertificateVerifyAPIView(BaseAPIView):
    """Public endpoint — verify certificate by QR token or code query param."""

    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get('code', '')
        service = _certificate_service()
        result = self.run_service(
            lambda: service.verify_code(code),
            action='certificate.verify',
        )
        return self.success(data=result, message='Certificate verified')
