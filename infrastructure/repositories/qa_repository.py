from django.db.models import QuerySet

from apps.qa.infrastructure.models import FAQ, UserQuestion, VisitorQuestion
from core.repositories.base import BaseRepository


class FAQRepository(BaseRepository[FAQ]):
    model_class = FAQ

    def active_faqs(self) -> QuerySet[FAQ]:
        return self.filter(is_active=True).order_by('sort_order', 'pk')


class UserQuestionRepository(BaseRepository[UserQuestion]):
    model_class = UserQuestion

    def get_queryset(self):
        return super().get_queryset().select_related('user', 'answered_by')

    def for_user(self, user) -> QuerySet[UserQuestion]:
        return self.filter(user=user).order_by('-created_at')

    def open_questions(self) -> QuerySet[UserQuestion]:
        return self.filter(status=UserQuestion.Status.OPEN).order_by('-created_at')


class VisitorQuestionRepository(BaseRepository[VisitorQuestion]):
    model_class = VisitorQuestion

    def get_queryset(self):
        return super().get_queryset().select_related('answered_by')

    def open_questions(self) -> QuerySet[VisitorQuestion]:
        return self.filter(status=VisitorQuestion.Status.OPEN).order_by('-created_at')
