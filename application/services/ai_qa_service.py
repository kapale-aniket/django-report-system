"""AI-assisted Q&A reply suggestions for admins."""
from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

from application.services.qa_service import QAService
from core.exceptions.base import BusinessLogicError, NotFoundAppError, PermissionAppError
from core.services.base import BaseService
from infrastructure.ai.llm_client import LLMClient, heuristic_qa_reply
from infrastructure.repositories.qa_repository import (
    UserQuestionRepository,
    VisitorQuestionRepository,
)

logger = logging.getLogger('reportflow.ai')


class AIQAService(BaseService):
    def __init__(
        self,
        qa_service: QAService | None = None,
        user_question_repository: UserQuestionRepository | None = None,
        visitor_question_repository: VisitorQuestionRepository | None = None,
    ):
        self.qa_service = qa_service or QAService()
        self.user_question_repository = user_question_repository or UserQuestionRepository()
        self.visitor_question_repository = visitor_question_repository or VisitorQuestionRepository()
        self.llm = LLMClient()

    def suggest_reply(self, user, *, question_id: int, question_type: str) -> dict[str, Any]:
        if not getattr(settings, 'AI_FEATURES_ENABLED', True):
            raise BusinessLogicError('AI features are disabled.')
        if getattr(user, 'role', None) != 'admin':
            raise PermissionAppError('Only admins can request AI reply suggestions.')

        question_type = (question_type or 'user').lower()
        if question_type == 'visitor':
            question = self.visitor_question_repository.get_by_id(question_id)
        else:
            question = self.user_question_repository.get_by_id(question_id)

        if question is None:
            raise NotFoundAppError('Question not found')

        subject = getattr(question, 'subject', '') or ''
        body = getattr(question, 'body', '') or ''
        faqs = [
            {'question': row.question, 'answer_text': row.answer_text}
            for row in self.qa_service.faq_list()
        ]

        if self.llm.is_configured():
            system_prompt = (
                'You help college platform administrators reply to user questions about '
                'report submissions, approvals, deadlines, and account access. '
                'Return strict JSON with keys: suggested_answer, confidence (low|medium|high). '
                'Use FAQ context when relevant. Be polite and concise.'
            )
            user_prompt = json.dumps(
                {
                    'subject': subject,
                    'question': body,
                    'faqs': faqs[:20],
                },
                ensure_ascii=False,
            )
            payload = self.llm.chat_json(system_prompt, user_prompt)
            if payload.get('suggested_answer'):
                return {
                    'question_id': question_id,
                    'question_type': question_type,
                    'suggested_answer': payload.get('suggested_answer', ''),
                    'confidence': payload.get('confidence', 'medium'),
                    'provider': 'openai',
                }

        fallback = heuristic_qa_reply(body, subject, faqs)
        return {
            'question_id': question_id,
            'question_type': question_type,
            'suggested_answer': fallback.get('suggested_answer', ''),
            'confidence': fallback.get('confidence', 'low'),
            'matched_faq_question': fallback.get('matched_faq_question', ''),
            'provider': fallback.get('provider', 'heuristic'),
        }
