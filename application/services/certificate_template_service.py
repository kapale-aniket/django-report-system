"""Certificate template management for admins."""
from __future__ import annotations

from typing import Any

from django.core.files.uploadedfile import UploadedFile

from apps.reports.certificate_design import merge_certificate_design, normalize_hex_color
from apps.reports.infrastructure.models import CertificateTemplate
from core.exceptions.base import NotFoundAppError, PermissionAppError, ValidationAppError
from core.services.base import BaseService
from django.contrib.auth import get_user_model
from django.utils import timezone
from infrastructure.pdf.certificate_builder import (
    CertificateContext,
    build_certificate_pdf_from_context,
)
from infrastructure.pdf.certificate_template_analyzer import analyze_reference_image

User = get_user_model()


class CertificateTemplateService(BaseService):
    """Configure certificate layouts — multiple templates, image analysis, preview."""

    def __init__(self):
        pass

    def _ensure_admin(self, user) -> None:
        if getattr(user, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only admins can manage certificate templates.')

    def list_templates(self):
        return CertificateTemplate.objects.order_by('-is_active', '-updated_at')

    def get_active_template(self) -> CertificateTemplate:
        return CertificateTemplate.get_active()

    def get_template(self, template_id: int) -> CertificateTemplate:
        template = CertificateTemplate.objects.filter(pk=template_id).first()
        if template is None:
            raise NotFoundAppError('Certificate template not found')
        return template

    def activate_template(self, user, template_id: int) -> CertificateTemplate:
        self._ensure_admin(user)
        template = self.get_template(template_id)
        CertificateTemplate.activate(template)
        return template

    def analyze_upload(self, uploaded) -> dict:
        return analyze_reference_image(uploaded)

    def _apply_palette(self, template: CertificateTemplate, palette: dict) -> None:
        template.accent_color = normalize_hex_color(palette.get('accent_color'), template.accent_color)
        template.secondary_color = normalize_hex_color(palette.get('secondary_color'), template.secondary_color)
        template.background_color = normalize_hex_color(palette.get('background_color'), template.background_color)
        template.text_color = normalize_hex_color(palette.get('text_color'), template.text_color)
        template.muted_color = normalize_hex_color(palette.get('muted_color'), template.muted_color)
        template.border_color = normalize_hex_color(
            palette.get('border_color') or palette.get('accent_color'),
            template.border_color,
        )
        template.name_color = normalize_hex_color(
            palette.get('name_color') or palette.get('accent_color'),
            template.name_color,
        )
        if 'use_reference_background' in palette:
            template.use_reference_background = bool(palette['use_reference_background'])
        template.style_json = palette.get('style_json', {})

    def _apply_analysis(self, template: CertificateTemplate, analysis: dict) -> None:
        self._apply_palette(template, analysis)
        merged = merge_certificate_design(template.design_json)
        suggested = analysis.get('design') or {}
        for section, values in suggested.items():
            if isinstance(values, dict) and isinstance(merged.get(section), dict):
                merged[section].update(values)
            else:
                merged[section] = values
        template.design_json = merged

    def save_from_form(self, user, form, *, activate: bool = True) -> CertificateTemplate:
        """Persist admin certificate designer form."""
        self._ensure_admin(user)
        if not form.is_valid():
            raise ValidationAppError('Please fix the highlighted certificate template fields.')

        template = form.save(commit=False)
        uploaded = form.cleaned_data.get('reference_image')
        if isinstance(uploaded, UploadedFile):
            analysis = self.analyze_upload(uploaded)
            self._apply_analysis(template, analysis)

        template.updated_by = user
        template.save()
        if activate:
            CertificateTemplate.activate(template)
        return template

    def preview_from_form(self, user, form) -> bytes:
        """Render sample PDF from unsaved form data."""
        self._ensure_admin(user)
        if not form.is_valid():
            raise ValidationAppError('Fix form errors before previewing the certificate template.')

        template = form.save(commit=False)
        return self._preview_bytes(template)

    def build_preview_pdf(self, user, template: CertificateTemplate | None = None) -> bytes:
        self._ensure_admin(user)
        template = template or CertificateTemplate.get_active()
        return self._preview_bytes(template)

    def _preview_bytes(self, template: CertificateTemplate) -> bytes:
        now = timezone.localtime(timezone.now())
        ctx = CertificateContext(
            student_name='Alex Johnson',
            project_title='Smart Campus Library Management System',
            department='Computer Science',
            roll_number='CS2024001',
            username='alex.j',
            academic_year='2025-2026',
            teacher_name='Dr. Priya Sharma',
            teacher_marks=88,
            final_marks=90,
            completion_date=now,
            submitted_date=now,
            verification_code='PREVIEW-SAMPLE-CODE',
            verify_url='https://example.com/certificates/verify/?code=PREVIEW-SAMPLE-CODE',
        )
        return build_certificate_pdf_from_context(ctx, template=template)

    def update_template(self, user, data: dict[str, Any], uploaded_file=None) -> CertificateTemplate:
        """Legacy helper — prefer save_from_form."""
        self._ensure_admin(user)
        template = CertificateTemplate.get_active()
        for field in data:
            if hasattr(template, field):
                setattr(template, field, data[field])
        if isinstance(uploaded_file, UploadedFile):
            analysis = self.analyze_upload(uploaded_file)
            template.reference_image = uploaded_file
            self._apply_analysis(template, analysis)
        template.updated_by = user
        template.save()
        CertificateTemplate.activate(template)
        return template
