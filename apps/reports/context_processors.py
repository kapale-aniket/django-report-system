def messaging_unread(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    from apps.messaging.infrastructure.models import Message

    unread_message_count = Message.objects.filter(receiver=request.user, is_read=False).count()
    return {'messaging_unread_count': unread_message_count}


def notification_badge(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}
    from apps.reports.infrastructure.models import Notification

    qs = Notification.objects.filter(
        user=request.user,
        notification_type=Notification.NotificationType.ALERT,
    )
    return {
        'notification_unread_count': qs.filter(is_read=False).count(),
        'recent_notifications': list(qs.order_by('-created_at')[:8]),
    }
