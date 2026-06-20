"""Async in-app notifications."""
from celery import shared_task


@shared_task(name='reportflow.notify_user')
def notify_user_task(user_id: int, message: str, link: str = '') -> None:
    from django.contrib.auth import get_user_model

    from apps.reports.infrastructure.models import Notification

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    if user is None:
        return
    Notification.objects.create(
        user=user,
        notification_type=Notification.NotificationType.ALERT,
        message=message[:2000],
        link=(link or '')[:500],
    )
