"""
Django settings — MySQL (project_db) + Enterprise API layer.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def _env_setting(name: str, default: str = '') -> str:
    """Return env value; treat blank/missing as default (empty env must not override)."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    value = str(raw).strip()
    return value or default


def _env_bool(name: str, default: str = 'false') -> bool:
    return _env_setting(name, default).lower() == 'true'


SECRET_KEY = _env_setting(
    'SECRET_KEY',
    'django-insecure-!)59-#v8-d$vm9*y%&60$fh)0ch1nzlw#4-c1bf40!fqkm(^ww',
)

DEBUG = _env_bool('DEBUG', 'true')

ALLOWED_HOSTS = [
    host.strip()
    for host in _env_setting('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if host.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'django_filters',
    'drf_spectacular',
    'apps.accounts.apps.AccountsConfig',
    'apps.reports.apps.ReportsConfig',
    'apps.messaging.apps.MessagingConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.qa.apps.QaConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'core.middleware.no_cache.NoCacheAuthenticatedMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SESSION_COOKIE_AGE = 7200
SESSION_SAVE_EVERY_REQUEST = True

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'apps.dashboard.context_processors.app_navigation',
                'apps.reports.context_processors.messaging_unread',
                'apps.reports.context_processors.notification_badge',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _env_setting('DB_NAME', 'project_reports_db'),
        'USER': _env_setting('DB_USER', 'postgres'),
        'PASSWORD': _env_setting('DB_PASSWORD', 'YOUR_POSTGRES_PASSWORD'),
        'HOST': _env_setting('DB_HOST', '127.0.0.1'),
        'PORT': _env_setting('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 7}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
X_FRAME_OPTIONS = 'SAMEORIGIN'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:post_login_redirect'

# --- REST Framework + JWT ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'core.authentication.jwt_optional.OptionalJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'core.pagination.StandardPagination',
    'PAGE_SIZE': 12,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'core.exceptions.handler.custom_exception_handler',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# --- API docs (Swagger / OpenAPI) ---
SPECTACULAR_SETTINGS = {
    'TITLE': 'ReportFlow API',
    'DESCRIPTION': 'College project report management — JWT + role-based workflows',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# --- Redis cache (falls back to locmem if Redis unavailable) ---
CACHE_TTL_DEFAULT = 300
REDIS_URL = _env_setting('REDIS_URL', 'redis://127.0.0.1:6379')
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': _env_setting('REDIS_CACHE_URL', f'{REDIS_URL}/1'),
    }
}

# --- Celery (eager mode in dev — set CELERY_TASK_ALWAYS_EAGER=False + run worker for prod) ---
CELERY_BROKER_URL = _env_setting('CELERY_BROKER_URL', f'{REDIS_URL}/0')
CELERY_RESULT_BACKEND = _env_setting('CELERY_RESULT_BACKEND', f'{REDIS_URL}/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = _env_bool('CELERY_TASK_ALWAYS_EAGER', 'true')
CELERY_TASK_EAGER_PROPAGATES = True
USE_CELERY_TASKS = True

# --- AI features (report review, OCR, Q&A assist) ---
AI_FEATURES_ENABLED = _env_bool('AI_FEATURES_ENABLED', 'true')
OPENAI_API_KEY = _env_setting('OPENAI_API_KEY', '')
OPENAI_API_BASE = _env_setting('OPENAI_API_BASE', 'https://api.openai.com/v1')
OPENAI_MODEL = _env_setting('OPENAI_MODEL', 'gpt-4o-mini')
AI_MAX_PDF_TEXT_CHARS = int(_env_setting('AI_MAX_PDF_TEXT_CHARS', '12000'))
AI_OCR_MIN_NATIVE_CHARS = int(_env_setting('AI_OCR_MIN_NATIVE_CHARS', '400'))
TESSERACT_CMD = _env_setting('TESSERACT_CMD', '')

# --- Centralized logging ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'reportflow.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'reportflow': {'handlers': ['console', 'file'], 'level': 'INFO'},
        'reportflow.api': {'handlers': ['console', 'file'], 'level': 'INFO'},
        'reportflow.audit': {'handlers': ['console', 'file'], 'level': 'INFO'},
        'reportflow.email': {'handlers': ['console', 'file'], 'level': 'INFO'},
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = _env_setting('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(_env_setting('EMAIL_PORT', '587'))
EMAIL_USE_TLS = _env_bool('EMAIL_USE_TLS', 'true')
EMAIL_USE_SSL = _env_bool('EMAIL_USE_SSL', 'false')
EMAIL_HOST_USER = _env_setting('EMAIL_HOST_USER', 'backendbyaniket@gmail.com')
EMAIL_HOST_PASSWORD = _env_setting('EMAIL_HOST_PASSWORD', 'tccrybgdpfstreux').replace(' ', '')
DEFAULT_FROM_EMAIL = _env_setting(
    'DEFAULT_FROM_EMAIL',
    f'ReportFlow <{EMAIL_HOST_USER}>',
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_TIMEOUT = int(_env_setting('EMAIL_TIMEOUT', '30'))
SITE_NAME = _env_setting('SITE_NAME', 'ReportFlow')
SITE_BASE_URL = _env_setting('SITE_BASE_URL', 'http://127.0.0.1:8000')
