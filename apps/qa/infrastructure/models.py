from django.conf import settings
from django.db import models


class QAItem(models.Model):
    """Unified FAQ, user questions, and visitor inquiries."""

    class QAType(models.TextChoices):
        FAQ = 'faq', 'FAQ'
        USER = 'user', 'User question'
        VISITOR = 'visitor', 'Visitor question'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        ANSWERED = 'answered', 'Answered'

    qa_type = models.CharField(max_length=20, choices=QAType.choices, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qa_items',
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True, default='')
    subject = models.CharField(max_length=200, blank=True)
    question = models.CharField(max_length=500, blank=True, help_text='FAQ question text.')
    body = models.TextField(blank=True, help_text='User/visitor question body.')
    answer_text = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qa_replies_given',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.qa_type == self.QAType.FAQ:
            return (self.question or self.subject or '')[:80]
        return f'{self.email or self.user_id} — {self.subject or self.body[:40]}'


class FAQManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(qa_type=QAItem.QAType.FAQ)

    def create(self, **kwargs):
        kwargs['qa_type'] = QAItem.QAType.FAQ
        if 'answer' in kwargs:
            kwargs['answer_text'] = kwargs.pop('answer')
        return super().create(**kwargs)


class FAQ(QAItem):
    objects = FAQManager()

    class Meta:
        proxy = True
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'

    @property
    def answer(self):
        return self.answer_text

    @answer.setter
    def answer(self, value):
        self.answer_text = value


class UserQuestionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(qa_type=QAItem.QAType.USER)

    def create(self, **kwargs):
        kwargs['qa_type'] = QAItem.QAType.USER
        return super().create(**kwargs)


class UserQuestion(QAItem):
    objects = UserQuestionManager()

    class Meta:
        proxy = True


class VisitorQuestionManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(qa_type=QAItem.QAType.VISITOR)

    def create(self, **kwargs):
        kwargs['qa_type'] = QAItem.QAType.VISITOR
        return super().create(**kwargs)


class VisitorQuestion(QAItem):
    objects = VisitorQuestionManager()

    class Meta:
        proxy = True
