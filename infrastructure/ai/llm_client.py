"""OpenAI-compatible chat client with heuristic fallback for Q&A."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger('reportflow.ai')


class LLMClient:
    def is_configured(self) -> bool:
        return bool(getattr(settings, 'OPENAI_API_KEY', ''))

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if self.is_configured():
            try:
                return self._openai_chat_json(system_prompt, user_prompt)
            except Exception as exc:
                logger.warning('LLM request failed, using heuristic fallback: %s', exc)
        return {}

    def _openai_chat_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        import httpx

        url = f"{settings.OPENAI_API_BASE.rstrip('/')}/chat/completions"
        payload = {
            'model': settings.OPENAI_MODEL,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            'temperature': 0.2,
            'response_format': {'type': 'json_object'},
        }
        headers = {
            'Authorization': f"Bearer {settings.OPENAI_API_KEY}",
            'Content-Type': 'application/json',
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        content = data['choices'][0]['message']['content']
        return json.loads(content)


def heuristic_qa_reply(question: str, subject: str, faqs: list[dict]) -> dict[str, Any]:
    """Match question keywords to FAQs for a draft admin reply."""
    query = f'{subject} {question}'.lower()
    query_tokens = set(re.findall(r'[a-z0-9]+', query))

    best_score = 0
    best_faq = None
    for faq in faqs:
        faq_text = f"{faq.get('question', '')} {faq.get('answer_text', '')}".lower()
        faq_tokens = set(re.findall(r'[a-z0-9]+', faq_text))
        if not faq_tokens:
            continue
        overlap = len(query_tokens & faq_tokens)
        score = overlap / max(len(query_tokens), 1)
        if score > best_score:
            best_score = score
            best_faq = faq

    if best_faq and best_score >= 0.15:
        answer = best_faq.get('answer_text') or ''
        return {
            'suggested_answer': answer,
            'matched_faq_question': best_faq.get('question', ''),
            'provider': 'heuristic',
            'confidence': 'medium' if best_score >= 0.3 else 'low',
        }

    return {
        'suggested_answer': (
            'Thank you for your question. '
            'Please allow us a short time to review your request and we will follow up with a detailed answer.'
        ),
        'matched_faq_question': '',
        'provider': 'heuristic',
        'confidence': 'low',
    }
