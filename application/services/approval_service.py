"""Teacher/admin approval workflow — delegates to ReportService."""
from __future__ import annotations

from application.services.report_service import ReportService
from core.services.base import BaseService


class ApprovalService(BaseService):
    """Approval commands extracted from report workflow."""

    def __init__(self, report_service: ReportService | None = None):
        self.report_service = report_service or ReportService()

    def teacher_approve(self, user, report_id: int, **kwargs):
        return self.report_service.teacher_approve(user, report_id, **kwargs)

    def teacher_reject(self, user, report_id: int, reason: str):
        return self.report_service.teacher_reject(user, report_id, reason)

    def admin_approve(self, user, report_id: int, marks: int | None = None):
        return self.report_service.admin_approve(user, report_id, marks)

    def admin_reject(self, user, report_id: int, reason: str):
        return self.report_service.admin_reject(user, report_id, reason)

    def bulk_admin_approve_or_reject(self, user, report_ids: list[int], action: str, reason: str = ''):
        return self.report_service.bulk_admin_approve_or_reject(user, report_ids, action, reason)
