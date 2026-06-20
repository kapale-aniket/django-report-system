from django.test import SimpleTestCase

from core.exceptions import PermissionAppError, ValidationAppError
from core.utils.user_messages import (
    GENERIC_ERROR,
    friendly_message,
    looks_technical,
)


class UserMessagesTests(SimpleTestCase):
    def test_app_error_uses_custom_message(self):
        self.assertEqual(
            friendly_message(ValidationAppError('Title is required.')),
            'Title is required.',
        )

    def test_technical_exception_is_sanitized(self):
        self.assertEqual(
            friendly_message(ValueError('unexpected service failure')),
            GENERIC_ERROR,
        )

    def test_traceback_is_technical(self):
        self.assertTrue(looks_technical('Traceback (most recent call last):'))

    def test_plain_sentence_is_not_technical(self):
        self.assertFalse(looks_technical('Invalid username or password'))
        self.assertEqual(
            friendly_message(PermissionAppError()),
            "You don't have permission to do that.",
        )
