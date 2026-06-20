from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import ActivityLog


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@receiver(user_logged_in)
def store_login_history(sender, request, user, **kwargs):
    ActivityLog.objects.create(
        user=user,
        action=ActivityLog.Action.LOGIN,
        ip_address=_client_ip(request) or '',
        user_agent=(request.META.get('HTTP_USER_AGENT') or '')[:512],
    )
