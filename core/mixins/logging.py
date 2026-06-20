import logging

logger = logging.getLogger('reportflow.audit')


class AuditLogMixin:
    """Mixin for API views to emit structured audit logs."""

    audit_logger = logger

    def log_action(self, action: str, user=None, detail: str = '', **extra):
        uid = getattr(user, 'id', None) if user else None
        self.audit_logger.info(
            action,
            extra={'user_id': uid, 'detail': detail, **extra},
        )
