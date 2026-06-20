"""Backward-compatible re-exports — canonical repos in infrastructure/repositories/."""
from infrastructure.repositories.report_repository import (
    ActivityLogRepository,
    NotificationRepository,
    ReportRepository,
)

__all__ = ['ActivityLogRepository', 'NotificationRepository', 'ReportRepository']
