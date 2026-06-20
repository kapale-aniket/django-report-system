"""
PDF certificate generation, audit logging, and email helpers.

Legacy shim — canonical implementations live in infrastructure/ and application/.
"""
from infrastructure.database.activity_log import log_activity
from infrastructure.email.smtp_sender import send_certificate_email, send_rejection_email
from infrastructure.pdf.certificate_builder import build_certificate_pdf

__all__ = [
    'build_certificate_pdf',
    'log_activity',
    'send_certificate_email',
    'send_rejection_email',
]
