"""In-app notification helper — queues via Celery when broker available."""
from apps.reports.infrastructure.models import Notification


def queue_user_notification(user, message: str, link: str = '') -> None:
    if not user or not getattr(user, 'pk', None):
        return
    from django.conf import settings

    if getattr(settings, 'USE_CELERY_TASKS', True):
        from tasks.celery_tasks.notification_tasks import notify_user_task

        notify_user_task.delay(user.pk, message[:2000], (link or '')[:500])
        return
    Notification.objects.create(
        user=user,
        notification_type=Notification.NotificationType.ALERT,
        message=message[:2000],
        link=(link or '')[:500],
    )
