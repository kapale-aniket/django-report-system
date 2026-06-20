"""User-facing message helpers — keep toast and API copy friendly and safe."""
from __future__ import annotations

GENERIC_ERROR = 'Something went wrong. Please try again.'
GENERIC_SAVE_ERROR = 'Something went wrong saving your data. Please try again.'
GENERIC_NOT_FOUND = "We couldn't find what you're looking for."
GENERIC_PERMISSION = "You don't have permission to do that."
GENERIC_AUTH = 'Please sign in to continue.'
GENERIC_VALIDATION = 'Please check your input and try again.'
GENERIC_BUSINESS = "This action isn't allowed right now."

_TECHNICAL_MARKERS = (
    'Traceback',
    'Error at',
    'File "',
    'IntegrityError',
    'DoesNotExist',
    'OperationalError',
    'ProgrammingError',
    'unexpected service',
    'Internal server error',
    'Database error',
)


def friendly_message(exc: BaseException | str | None, *, fallback: str = GENERIC_ERROR) -> str:
    """Return a safe, user-facing message for toasts and pages."""
    if exc is None:
        return fallback
    if not isinstance(exc, str):
        from core.exceptions.base import AppError

        if isinstance(exc, AppError):
            return exc.message
    text = str(exc).strip()
    if not text:
        return fallback
    if looks_technical(text):
        return fallback
    if len(text) > 280:
        return text[:277] + '…'
    return text


def looks_technical(text: str) -> bool:
    """True when text looks like a stack trace or developer error."""
    if not text:
        return False
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in _TECHNICAL_MARKERS)
