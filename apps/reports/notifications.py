"""In-app notifications (no external services)."""

from .models import Notification


def create_in_app_notification(user, message: str, link: str = '') -> None:
    if not user or not getattr(user, 'pk', None):
        return
    Notification.objects.create(
        user=user,
        message=message[:2000],
        link=(link or '')[:500],
    )
