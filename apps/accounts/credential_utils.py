"""Short username/password generation for admin-created accounts."""
import re
import secrets
import string

MAX_USERNAME_LEN = 7
MAX_PASSWORD_LEN = 7
_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def _name_prefix(first_name: str, last_name: str, email: str) -> str:
    for value in (first_name, last_name, (email or '').split('@')[0], 'user'):
        cleaned = re.sub(r'[^a-z0-9]', '', (value or '').lower())
        if cleaned:
            return cleaned[: MAX_USERNAME_LEN - 1]
    return 'u'


def generate_short_username(
    *,
    first_name: str = '',
    last_name: str = '',
    email: str = '',
    exists,
) -> str:
    """Build username: name prefix + random suffix, total length <= 7."""
    prefix = _name_prefix(first_name, last_name, email)
    for _ in range(80):
        suffix_len = max(1, MAX_USERNAME_LEN - len(prefix))
        if len(prefix) + suffix_len > MAX_USERNAME_LEN:
            prefix = prefix[: MAX_USERNAME_LEN - suffix_len]
        suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(suffix_len))
        candidate = (prefix + suffix)[:MAX_USERNAME_LEN]
        if candidate and not exists(candidate):
            return candidate
    fallback = ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(MAX_USERNAME_LEN))
    if exists(fallback):
        raise ValueError('Could not generate a unique username')
    return fallback


def generate_short_password(length: int = MAX_PASSWORD_LEN) -> str:
    return ''.join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))
