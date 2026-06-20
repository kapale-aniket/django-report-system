from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.qa.infrastructure.models import UserQuestion, VisitorQuestion
from infrastructure.repositories.qa_repository import (
    FAQRepository,
    UserQuestionRepository,
    VisitorQuestionRepository,
)
from apps.qa.utils import send_visitor_answer_email
from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError

User = get_user_model()


class QAService:
    """Application service for FAQ and Q&A workflows."""

    def __init__(
        self,
        faq_repository: FAQRepository | None = None,
        user_question_repository: UserQuestionRepository | None = None,
        visitor_question_repository: VisitorQuestionRepository | None = None,
    ):
        self.faq_repository = faq_repository or FAQRepository()
        self.user_question_repository = user_question_repository or UserQuestionRepository()
        self.visitor_question_repository = visitor_question_repository or VisitorQuestionRepository()

    def faq_list(self):
        return list(self.faq_repository.active_faqs())

    def ask_question(self, user, *, subject: str = '', body: str):
        body = (body or '').strip()
        if not body:
            raise BusinessLogicError('Question body is required')
        return self.user_question_repository.create(
            {
                'user': user,
                'subject': (subject or '').strip(),
                'body': body,
            }
        )

    def question_list(self, user):
        my_questions = list(self.user_question_repository.for_user(user)[:50])
        pending_user_questions = []
        pending_visitor_questions = []
        if getattr(user, 'role', None) == User.Role.ADMIN:
            pending_user_questions = list(self.user_question_repository.open_questions()[:100])
            pending_visitor_questions = list(self.visitor_question_repository.open_questions()[:100])
        return {
            'my_questions': my_questions,
            'pending_user_questions': pending_user_questions,
            'pending_visitor_questions': pending_visitor_questions,
        }

    def reply(self, admin, question_id: int, *, answer_text: str):
        if getattr(admin, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only administrators can reply to questions')

        answer_text = (answer_text or '').strip()
        if not answer_text:
            raise BusinessLogicError('Reply text is required')

        question = self.user_question_repository.get_by_id(question_id)
        if question is None:
            raise NotFoundAppError('Question not found')
        if question.status != UserQuestion.Status.OPEN:
            raise BusinessLogicError('This question is already answered')

        return self.user_question_repository.update(
            question,
            {
                'answer_text': answer_text,
                'status': UserQuestion.Status.ANSWERED,
                'answered_by': admin,
                'answered_at': timezone.now(),
            },
        )

    def visitor_ask(self, *, name: str = '', email: str, subject: str = '', body: str):
        email = (email or '').strip()
        body = (body or '').strip()
        if not email:
            raise BusinessLogicError('Email is required')
        if not body:
            raise BusinessLogicError('Question body is required')
        return self.visitor_question_repository.create(
            {
                'name': (name or '').strip(),
                'email': email,
                'subject': (subject or '').strip(),
                'body': body,
            }
        )

    def visitor_reply(self, admin, question_id: int, *, answer_text: str):
        if getattr(admin, 'role', None) != User.Role.ADMIN:
            raise PermissionAppError('Only administrators can reply to visitor questions')

        answer_text = (answer_text or '').strip()
        if not answer_text:
            raise BusinessLogicError('Reply text is required')

        question = self.visitor_question_repository.get_by_id(question_id)
        if question is None:
            raise NotFoundAppError('Visitor question not found')
        if question.status != VisitorQuestion.Status.OPEN:
            raise BusinessLogicError('This inquiry is already answered')

        updated = self.visitor_question_repository.update(
            question,
            {
                'answer_text': answer_text,
                'status': VisitorQuestion.Status.ANSWERED,
                'answered_by': admin,
                'answered_at': timezone.now(),
            },
        )
        send_visitor_answer_email(updated)
        return updated
