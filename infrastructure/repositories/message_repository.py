from django.db.models import Q, QuerySet

from apps.messaging.infrastructure.models import Message
from core.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    model_class = Message

    def get_queryset(self):
        return super().get_queryset().select_related('sender', 'receiver')

    def inbox_for(self, user) -> QuerySet[Message]:
        return self.filter(receiver=user).order_by('-created_at')

    def sent_for(self, user) -> QuerySet[Message]:
        return self.filter(sender=user).order_by('-created_at')

    def unread_count_for(self, user) -> int:
        return self.count(receiver=user, is_read=False)

    def get_for_participant(self, message_id: int, user):
        return self.get_queryset().filter(pk=message_id).filter(
            Q(receiver=user) | Q(sender=user)
        ).first()

    def mark_read(self, message: Message) -> Message:
        if not message.is_read:
            message.is_read = True
            message.save(update_fields=['is_read'])
        return message
