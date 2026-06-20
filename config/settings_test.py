"""Test settings — SQLite, in-memory email, no Redis."""
import tempfile
from pathlib import Path

from config.settings import *  # noqa: F403,F401

BASE_DIR = Path(__file__).resolve().parent.parent

TEST_MEDIA_ROOT = Path(tempfile.mkdtemp(prefix='reportflow_test_media_'))

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

MEDIA_ROOT = TEST_MEDIA_ROOT
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'testserver']
AI_FEATURES_ENABLED = True
OPENAI_API_KEY = ''

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {'null': {'class': 'logging.NullHandler'}},
    'root': {'handlers': ['null']},
}
