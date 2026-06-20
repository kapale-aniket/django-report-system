"""Activity audit logging."""
from apps.reports.infrastructure.models import ActivityLog


def log_activity(user, action, report=None, detail=''):
    ActivityLog.objects.create(user=user, action=action, report=report, detail=detail[:500])
