from rest_framework import status
from rest_framework.permissions import AllowAny

from core.permissions.roles import IsAdmin, IsAuthenticatedRole
from api.base.base_api_view import BaseAPIView

from application.services.qa_service import QAService
from application.services.ai_qa_service import AIQAService
from infrastructure.repositories.qa_repository import (
    FAQRepository,
    UserQuestionRepository,
    VisitorQuestionRepository,
)
from api.serializers.qa import (
    AskQuestionSerializer,
    FAQSerializer,
    ReplySerializer,
    UserQuestionSerializer,
    VisitorAskSerializer,
    VisitorQuestionSerializer,
)
from api.serializers.ai import SuggestReplySerializer


class QAServiceMixin:
    service_class = QAService
    faq_repository_class = FAQRepository
    user_question_repository_class = UserQuestionRepository
    visitor_question_repository_class = VisitorQuestionRepository

    def get_qa_service(self) -> QAService:
        return self.service_class(
            faq_repository=self.faq_repository_class(),
            user_question_repository=self.user_question_repository_class(),
            visitor_question_repository=self.visitor_question_repository_class(),
        )


class FAQListAPIView(QAServiceMixin, BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        service = self.get_qa_service()
        faqs = self.run_service(lambda: service.faq_list(), action='qa.faq_list')
        return self.success(
            data={'faqs': FAQSerializer(faqs, many=True).data},
            message='FAQs retrieved successfully',
        )


class AskQuestionAPIView(QAServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def post(self, request):
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_qa_service()
        question = self.run_service(
            lambda: service.ask_question(
                request.user,
                subject=serializer.validated_data.get('subject', ''),
                body=serializer.validated_data['body'],
            ),
            action='qa.ask_question',
            user=request.user,
        )
        return self.success(
            data=UserQuestionSerializer(question).data,
            message='Question submitted successfully',
            status_code=status.HTTP_201_CREATED,
        )


class QuestionListAPIView(QAServiceMixin, BaseAPIView):
    permission_classes = [IsAuthenticatedRole]

    def get(self, request):
        service = self.get_qa_service()
        payload = self.run_service(
            lambda: service.question_list(request.user),
            action='qa.question_list',
            user=request.user,
        )
        return self.success(
            data={
                'my_questions': UserQuestionSerializer(payload['my_questions'], many=True).data,
                'pending_user_questions': UserQuestionSerializer(
                    payload['pending_user_questions'],
                    many=True,
                ).data,
                'pending_visitor_questions': VisitorQuestionSerializer(
                    payload['pending_visitor_questions'],
                    many=True,
                ).data,
            },
            message='Questions retrieved successfully',
        )


class ReplyQuestionAPIView(QAServiceMixin, BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, question_id: int):
        serializer = ReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_qa_service()
        question = self.run_service(
            lambda: service.reply(
                request.user,
                question_id,
                answer_text=serializer.validated_data['answer_text'],
            ),
            action='qa.reply',
            user=request.user,
        )
        return self.success(
            data=UserQuestionSerializer(question).data,
            message='Reply saved successfully',
        )


class VisitorAskAPIView(QAServiceMixin, BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VisitorAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_qa_service()
        question = self.run_service(
            lambda: service.visitor_ask(
                name=serializer.validated_data.get('name', ''),
                email=serializer.validated_data['email'],
                subject=serializer.validated_data.get('subject', ''),
                body=serializer.validated_data['body'],
            ),
            action='qa.visitor_ask',
        )
        return self.success(
            data=VisitorQuestionSerializer(question).data,
            message='Question received successfully',
            status_code=status.HTTP_201_CREATED,
        )


class VisitorReplyAPIView(QAServiceMixin, BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request, question_id: int):
        serializer = ReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = self.get_qa_service()
        question = self.run_service(
            lambda: service.visitor_reply(
                request.user,
                question_id,
                answer_text=serializer.validated_data['answer_text'],
            ),
            action='qa.visitor_reply',
            user=request.user,
        )
        return self.success(
            data=VisitorQuestionSerializer(question).data,
            message='Visitor reply saved successfully',
        )


class SuggestReplyAPIView(BaseAPIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = SuggestReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = AIQAService()
        payload = self.run_service(
            lambda: service.suggest_reply(
                request.user,
                question_id=serializer.validated_data['question_id'],
                question_type=serializer.validated_data['question_type'],
            ),
            action='qa.suggest_reply',
            user=request.user,
        )
        return self.success(data=payload, message='Suggested reply generated')
