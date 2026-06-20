from rest_framework import status

from core.permissions.roles import IsAuthenticatedRole
from api.base.base_api_view import BaseAPIView

from application.services.messaging_service import MessagingService
from infrastructure.repositories.message_repository import MessageRepository
from api.serializers.messaging import (
    ComposeMessageSerializer,
    MessageSerializer,
    ReplyMessageSerializer,
)


class MessagingServiceMixin:
    service_class = MessagingService
    repository_class = MessageRepository

    def get_messaging_service(self) -> MessagingService:
        return self.service_class(repository=self.repository_class())


class InboxAPIView(MessagingServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request):
        service = self.get_messaging_service()
        messages = self.run_service(
            lambda: service.inbox(request.user),
            action='messaging.inbox',
            user=request.user,
        )
        data = MessageSerializer(messages, many=True).data
        return self.success(
            data={
                'messages': data,
                'unread_count': service.unread_count(request.user),
            },
            message='Inbox retrieved successfully',
        )


class SentAPIView(MessagingServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request):
        service = self.get_messaging_service()
        messages = self.run_service(
            lambda: service.sent(request.user),
            action='messaging.sent',
            user=request.user,
        )
        return self.success(
            data={'messages': MessageSerializer(messages, many=True).data},
            message='Sent messages retrieved successfully',
        )


class ComposeAPIView(MessagingServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request):
        serializer = ComposeMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_messaging_service()
        message = self.run_service(
            lambda: service.compose(
                request.user,
                receiver_id=serializer.validated_data['receiver_id'],
                body=serializer.validated_data['body'],
            ),
            action='messaging.compose',
            user=request.user,
        )
        return self.success(
            data=MessageSerializer(message).data,
            message='Message sent successfully',
            status_code=status.HTTP_201_CREATED,
        )


class ReplyAPIView(MessagingServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request, message_id: int):
        serializer = ReplyMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_messaging_service()
        message = self.run_service(
            lambda: service.reply(
                request.user,
                message_id,
                body=serializer.validated_data['body'],
            ),
            action='messaging.reply',
            user=request.user,
        )
        return self.success(
            data=MessageSerializer(message).data,
            message='Reply sent successfully',
            status_code=status.HTTP_201_CREATED,
        )


class MarkReadAPIView(MessagingServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request, message_id: int):
        service = self.get_messaging_service()
        message = self.run_service(
            lambda: service.mark_read(request.user, message_id),
            action='messaging.mark_read',
            user=request.user,
        )
        return self.success(
            data=MessageSerializer(message).data,
            message='Message marked as read',
        )
