"""PDF certificate generation with embedded QR verification code."""
from infrastructure.pdf.certificate_builder import (
    CertificateContext,
    build_certificate_pdf,
    build_certificate_pdf_from_context,
    build_certificate_pdf_from_report,
    certificate_context_from_report,
    marks_to_grade,
)

__all__ = [
    'CertificateContext',
    'build_certificate_pdf',
    'build_certificate_pdf_from_context',
    'build_certificate_pdf_from_report',
    'certificate_context_from_report',
    'marks_to_grade',
]
