"""Base filter utilities for list endpoints."""


class BaseFilterMixin:
    """Mixin for services/repositories that accept filter dicts."""

    @staticmethod
    def clean_filter_value(value):
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
