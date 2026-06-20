"""Public certificate verification URLs for QR codes and share links."""
from urllib.parse import urlencode

from django.conf import settings


def build_public_certificate_verify_url(verification_code: str) -> str:
    """Absolute URL embedded in certificate QR codes (scannable from any device)."""
    site_base_url = (getattr(settings, 'SITE_BASE_URL', '') or 'http://127.0.0.1:8000').rstrip('/')
    query = urlencode({'code': verification_code})
    return f'{site_base_url}/certificates/verify/?{query}'
