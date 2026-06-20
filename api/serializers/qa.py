from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.qa.infrastructure.models import FAQ, UserQuestion, VisitorQuestion

User = get_user_model()


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ('id', 'question', 'answer', 'sort_order', 'updated_at')


class UserQuestionSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserQuestion
        fields = (
            'id',
            'user_id',
            'username',
            'subject',
            'body',
            'status',
            'created_at',
            'answer_text',
            'answered_at',
            'answered_by',
        )
        read_only_fields = fields


class VisitorQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorQuestion
        fields = (
            'id',
            'name',
            'email',
            'subject',
            'body',
            'status',
            'created_at',
            'answer_text',
            'answered_at',
            'answered_by',
        )
        read_only_fields = fields


class AskQuestionSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=200, required=False, allow_blank=True)
    body = serializers.CharField(max_length=5000, trim_whitespace=True)


class VisitorAskSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=200, required=False, allow_blank=True)
    body = serializers.CharField(max_length=5000, trim_whitespace=True)


class ReplySerializer(serializers.Serializer):
    answer_text = serializers.CharField(max_length=5000, trim_whitespace=True)
