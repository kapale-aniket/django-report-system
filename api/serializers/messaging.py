from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.messaging.infrastructure.models import Message

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'role')


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    receiver = UserSummarySerializer(read_only=True)

    class Meta:
        model = Message
        fields = (
            'id',
            'sender',
            'receiver',
            'body',
            'is_read',
            'created_at',
        )
        read_only_fields = fields


class ComposeMessageSerializer(serializers.Serializer):
    receiver_id = serializers.IntegerField(min_value=1)
    body = serializers.CharField(max_length=5000, trim_whitespace=True)


class ReplyMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=5000, trim_whitespace=True)
