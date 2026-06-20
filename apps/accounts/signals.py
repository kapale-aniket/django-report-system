from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User


def _build_roll_number(user: User) -> str:
    raw = (user.department or 'GEN').upper().replace(' ', '')[:4] or 'GEN'
    year = str(timezone.now().year)[-2:]
    return f'{raw}{year}{user.pk:05d}'


@receiver(post_save, sender=User)
def assign_student_roll_number(sender, instance: User, created, **kwargs):
    if instance.role != User.Role.STUDENT:
        return
    if instance.roll_number:
        return
    if not instance.pk:
        return
    roll = _build_roll_number(instance)
    User.objects.filter(pk=instance.pk).update(roll_number=roll)
