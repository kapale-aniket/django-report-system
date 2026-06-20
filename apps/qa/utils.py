"""Email helpers for Q&A (optional; fails silently if mail is not configured)."""

from django.conf import settings
from django.core.mail import send_mail


def send_visitor_answer_email(visitor_question) -> None:
    """Notify visitor by email when an admin posts a reply."""
    email = (visitor_question.email or '').strip()
    if not email:
        return
    name = (visitor_question.name or '').strip()
    greeting = f'Hello {name},\n\n' if name else 'Hello,\n\n'
    subject = f'Re: {visitor_question.subject or "Your ReportFlow question"}'
    body = (
        f'{greeting}'
        f'{visitor_question.answer_text}\n\n'
        f'— ReportFlow support\n'
        f'(Your original question: {visitor_question.body[:500]}{"…" if len(visitor_question.body) > 500 else ""})'
    )
    try:
        send_mail(
            subject=subject[:200],
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'noreply@localhost',
            recipient_list=[email],
            fail_silently=True,
        )
    except Exception:
        pass
