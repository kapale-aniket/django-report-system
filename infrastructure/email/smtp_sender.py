"""Email delivery helpers."""
import logging

from django.conf import settings
from django.core.mail import get_connection, send_mail

logger = logging.getLogger('reportflow.email')


def _smtp_connection():
    return get_connection(
        backend=settings.EMAIL_BACKEND,
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
        use_ssl=getattr(settings, 'EMAIL_USE_SSL', False),
        timeout=getattr(settings, 'EMAIL_TIMEOUT', 30),
        fail_silently=False,
    )


def _deliver_plain_email(*, subject: str, message: str, to_email: str) -> None:
    if not settings.EMAIL_HOST:
        raise ValueError('EMAIL_HOST is not configured')
    if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
        raise ValueError('EMAIL_HOST_USER and EMAIL_HOST_PASSWORD are required')

    connection = _smtp_connection()
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[to_email],
        connection=connection,
        auth_user=settings.EMAIL_HOST_USER,
        auth_password=settings.EMAIL_HOST_PASSWORD,
        fail_silently=False,
    )


def send_welcome_credentials_email(
    *,
    to_email: str,
    first_name: str,
    username: str,
    password: str,
    role: str,
) -> None:
    from infrastructure.email.messages import normalize_email

    to_email = normalize_email(to_email)
    if not to_email:
        raise ValueError('Recipient email address is missing.')
    site_name = getattr(settings, 'SITE_NAME', 'ReportFlow')
    base_url = getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')
    login_url = f'{base_url}/accounts/login/'
    greeting = first_name.strip() or username
    role_label = {'student': 'Student', 'teacher': 'Teacher'}.get(role, role.title())
    message = (
        f'Hello {greeting},\n\n'
        f'An administrator created your {site_name} {role_label} account.\n\n'
        f'Username: {username}\n'
        f'Password: {password}\n\n'
        f'Sign in here: {login_url}\n\n'
        'Use these credentials to access your dashboard. '
        'If you forget your password, use "Forgot password?" on the sign-in page.\n\n'
        f'- {site_name}'
    )
    try:
        _deliver_plain_email(
            subject=f'Your {site_name} login credentials',
            message=message,
            to_email=to_email,
        )
        logger.info('Sent welcome credentials email to %s', to_email)
    except Exception as exc:
        logger.exception(
            'Failed to send welcome credentials to %s via %s:%s — %s',
            to_email,
            settings.EMAIL_HOST,
            settings.EMAIL_PORT,
            exc,
        )
        raise


def send_rejection_email(report, reason: str) -> None:
    user = report.student
    if not user.email:
        return
    try:
        _deliver_plain_email(
            subject='Project report requires revision',
            message=(
                f'Hello {user.get_full_name() or user.username},\n\n'
                f'Your report "{report.title}" was rejected.\n\n'
                f'Reason:\n{reason}\n\n'
                'Please sign in and upload a revised PDF.\n'
            ),
            to_email=user.email,
        )
    except Exception:
        logger.exception('Failed to send rejection email for report %s', report.pk)


def send_certificate_email(report, pdf_bytes: bytes) -> None:
    """Backward-compatible wrapper — prefer send_admin_final_approval_email with pdf_bytes."""
    from infrastructure.email.report_status_emails import send_admin_final_approval_email

    send_admin_final_approval_email(report, pdf_bytes=pdf_bytes)
