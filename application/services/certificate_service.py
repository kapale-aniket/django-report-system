"""Certificate generation and QR verification."""
from __future__ import annotations

import secrets
from typing import Any

from apps.reports.group_helpers import report_stakeholder_ids, report_stakeholder_users
from apps.reports.infrastructure.models import Report
from core.exceptions.base import NotFoundAppError, PermissionAppError, ValidationAppError
from core.services.base import BaseService
from core.utils.certificate_urls import build_public_certificate_verify_url
from django.contrib.auth import get_user_model
from django.utils import timezone
from infrastructure.pdf.certificate_builder import build_certificate_pdf_from_report
from infrastructure.repositories.report_repository import ReportRepository

User = get_user_model()


def _active_certificate_template():
    from apps.reports.infrastructure.models import CertificateTemplate

    return CertificateTemplate.get_active()


class CertificateService(BaseService):
    """Issue PDF certificates and verify authenticity via QR token."""

    def __init__(self, report_repository: ReportRepository | None = None):
        self.report_repository = report_repository or ReportRepository()

    def ensure_verification_code(self, report) -> str:
        if report.certificate_verification_code:
            return report.certificate_verification_code
        code = secrets.token_urlsafe(12)
        report.certificate_verification_code = code
        report.save(update_fields=['certificate_verification_code'])
        return code

    def ensure_verification_code_for_recipient(self, report, recipient) -> str:
        if recipient.pk == report.student_id:
            return self.ensure_verification_code(report)

        codes = dict(report.certificate_member_codes_json or {})
        key = str(recipient.pk)
        if key not in codes:
            codes[key] = secrets.token_urlsafe(12)
            report.certificate_member_codes_json = codes
            report.save(update_fields=['certificate_member_codes_json'])
        return codes[key]

    def ensure_all_recipient_codes(self, report) -> None:
        """Pre-generate unique verification codes for every group member."""
        for recipient in self.certificate_recipients(report):
            self.ensure_verification_code_for_recipient(report, recipient)

    def verification_code_for_user(self, report, user) -> str | None:
        if not report.is_certificate_eligible:
            return None
        if user.pk not in report_stakeholder_ids(report):
            return None
        if user.pk == report.student_id:
            return report.certificate_verification_code or self.ensure_verification_code_for_recipient(
                report, user
            )
        codes = report.certificate_member_codes_json or {}
        return codes.get(str(user.pk)) or self.ensure_verification_code_for_recipient(report, user)

    def _resolve_recipient(self, report, recipient=None):
        return recipient or report.student

    def build_pdf_bytes(self, report, *, recipient=None) -> bytes:
        if not report.is_certificate_eligible:
            raise ValidationAppError(
                'Certificate is available only when the teacher marked this as the final submission '
                'and the report is fully approved.'
            )
        recipient = self._resolve_recipient(report, recipient)
        code = self.ensure_verification_code_for_recipient(report, recipient)
        verify_url = build_public_certificate_verify_url(code)
        return build_certificate_pdf_from_report(
            report,
            verification_code=code,
            verify_url=verify_url,
            template=_active_certificate_template(),
            recipient=recipient,
        )

    def get_certificate_for_user(self, user, report_id: int) -> bytes:
        report = (
            Report.objects.select_related('student', 'student__assigned_teacher', 'assigned_teacher', 'rubric')
            .prefetch_related('group__members')
            .filter(pk=report_id)
            .first()
        )
        if report is None:
            raise NotFoundAppError('Report not found')
        if not report.is_certificate_eligible:
            raise ValidationAppError(
                'Certificate is not available. The teacher must mark the submission as final, '
                'and the report must be approved by both teacher and admin.'
            )
        role = getattr(user, 'role', None)
        if role == User.Role.ADMIN:
            recipient = report.student
        elif role == User.Role.TEACHER:
            from apps.reports.teacher_helpers import teacher_can_access_report

            if not teacher_can_access_report(user, report):
                raise PermissionAppError('Not your assigned project')
            recipient = report.student
        elif role == User.Role.STUDENT:
            if user.pk not in report_stakeholder_ids(report):
                raise PermissionAppError('Not your report')
            recipient = user
        else:
            raise PermissionAppError('Permission denied')
        return self.build_pdf_bytes(report, recipient=recipient)

    def _find_report_and_recipient_by_code(self, code: str):
        report = (
            Report.objects.select_related('student')
            .filter(
                certificate_verification_code=code,
                status=Report.Status.APPROVED,
                is_final_submission=True,
            )
            .first()
        )
        if report is not None:
            return report, report.student

        candidate_reports = Report.objects.select_related('student').filter(
            status=Report.Status.APPROVED,
            is_final_submission=True,
        )
        for candidate in candidate_reports:
            member_codes = candidate.certificate_member_codes_json or {}
            for user_id, member_code in member_codes.items():
                if member_code != code:
                    continue
                recipient = User.objects.filter(pk=int(user_id)).first()
                if recipient is not None:
                    return candidate, recipient
        return None, None

    def verify_code(self, code: str) -> dict[str, Any]:
        code = (code or '').strip()
        if not code:
            raise ValidationAppError('Verification code is required')

        report, recipient = self._find_report_and_recipient_by_code(code)
        if report is None or recipient is None:
            raise NotFoundAppError('Certificate not found or invalid')

        from infrastructure.pdf.certificate_builder import marks_to_grade

        letter, grade_label = marks_to_grade(report.teacher_marks)
        completion = report.updated_at
        if completion and timezone.is_aware(completion):
            completion = timezone.localtime(completion)
        return {
            'valid': True,
            'report_id': report.pk,
            'project_title': report.title,
            'student_name': recipient.get_full_name() or recipient.username,
            'student_username': recipient.username,
            'department': getattr(recipient, 'department', '') or '',
            'roll_number': getattr(recipient, 'roll_number', '') or '',
            'academic_year': report.academic_year or '',
            'teacher_marks': report.teacher_marks,
            'grade': letter,
            'grade_label': grade_label,
            'marks': report.marks,
            'is_final_submission': report.is_final_submission,
            'completion_date': completion.isoformat() if completion else None,
            'approved_at': report.updated_at.isoformat() if report.updated_at else None,
            'verification_code': code,
            'is_group_project': bool(report.group_id),
        }

    def certificate_recipients(self, report) -> list:
        recipients = report_stakeholder_users(report)
        return recipients or ([report.student] if report.student_id else [])
