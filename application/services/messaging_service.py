from django.contrib.auth import get_user_model

from infrastructure.repositories.message_repository import MessageRepository
from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError
from core.services.base import BaseService

User = get_user_model()


class MessagingService(BaseService[MessageRepository]):
    repository_class = MessageRepository

    def inbox(self, user):
        return list(self.repository.inbox_for(user)[:100])

    def sent(self, user):
        return list(self.repository.sent_for(user)[:100])

    def unread_count(self, user) -> int:
        return self.repository.unread_count_for(user)

    def compose(self, sender, *, receiver_id: int, body: str):
        body = (body or '').strip()
        if not body:
            raise BusinessLogicError('Message body is required')

        receiver = User.objects.filter(pk=receiver_id, is_active=True).first()
        if receiver is None:
            raise NotFoundAppError('Receiver not found')
        if receiver.pk == sender.pk:
            raise BusinessLogicError('You cannot send a message to yourself')

        return self.repository.create(
            {
                'sender': sender,
                'receiver': receiver,
                'body': body,
            }
        )

    def reply(self, user, message_id: int, *, body: str):
        original = self.repository.get_for_participant(message_id, user)
        if original is None:
            raise NotFoundAppError('Message not found')

        receiver = original.sender if original.receiver_id == user.pk else original.receiver
        return self.compose(sender=user, receiver_id=receiver.pk, body=body)

    def mark_read(self, user, message_id: int):
        message = self.repository.get_for_participant(message_id, user)
        if message is None:
            raise NotFoundAppError('Message not found')
        if message.receiver_id != user.pk:
            raise PermissionAppError('Only the recipient can mark a message as read')
        return self.repository.mark_read(message)
