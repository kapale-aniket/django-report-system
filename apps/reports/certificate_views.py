"""Public certificate verification pages."""
from django.shortcuts import render
from django.urls import reverse

from application.services.certificate_service import CertificateService
from apps.accounts.infrastructure.models import User
from apps.reports.views import _safe_back_url
from core.utils.certificate_urls import build_public_certificate_verify_url
from core.exceptions.base import NotFoundAppError, ValidationAppError


def _verify_back_context(request) -> dict[str, str]:
    """Back link for verify page — staff/students get Back; public visitors get Home."""
    next_url = _safe_back_url(request)
    if next_url:
        return {'back_url': next_url, 'back_label': 'Back'}

    if request.user.is_authenticated:
        role = getattr(request.user, 'role', None)
        if role == User.Role.TEACHER:
            return {'back_url': reverse('reports:list'), 'back_label': 'Back'}
        if role == User.Role.ADMIN:
            return {'back_url': reverse('reports:list'), 'back_label': 'Back'}
        if role == User.Role.STUDENT:
            return {'back_url': reverse('reports:my_reports'), 'back_label': 'Back'}

    return {'back_url': reverse('dashboard:landing'), 'back_label': 'Home'}


def verify_certificate_page(request):
    """Public page — scan QR or enter a certificate verification code."""
    verification_code = (request.GET.get('code') or request.POST.get('code') or '').strip()
    verification_result = None
    verification_error = None

    if verification_code:
        try:
            verification_result = CertificateService().verify_code(verification_code)
        except ValidationAppError as exc:
            verification_error = exc.message
        except NotFoundAppError:
            verification_error = 'Certificate not found. Check the code or contact your college administrator.'

    public_verify_url = (
        build_public_certificate_verify_url(verification_code) if verification_code else ''
    )

    return render(
        request,
        'certificates/verify.html',
        {
            'verification_code': verification_code,
            'verification_result': verification_result,
            'verification_error': verification_error,
            'public_verify_url': public_verify_url,
            **_verify_back_context(request),
        },
    )
