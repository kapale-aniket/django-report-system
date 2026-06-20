"""Redis cache configuration helpers."""
from django.conf import settings
from django.core.cache import cache


def get_cache_backend() -> str:
    return settings.CACHES['default']['BACKEND']


def cache_get(key: str, default=None):
    return cache.get(key, default)


def cache_set(key: str, value, timeout: int | None = None) -> None:
    cache.set(key, value, timeout=timeout or settings.CACHE_TTL_DEFAULT)
