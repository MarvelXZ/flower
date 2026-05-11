"""Base Django settings for the Flower backend.

The project uses django-tenants with a modular-monolith layout. Public schema
apps are kept separate from tenant schema apps so tenant isolation remains
visible in configuration, not just in application code.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from environs import Env

env = Env()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

SECRET_KEY = env.str("DJANGO_SECRET_KEY", default=os.environ.get("SECRET_KEY", ""))
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY or SECRET_KEY must be set.")

if "DJANGO_DEBUG" in os.environ:
    DEBUG = env.bool("DJANGO_DEBUG")
else:
    DEBUG = env.bool("DEBUG", default=False)

if "DJANGO_ALLOWED_HOSTS" in os.environ:
    ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
else:
    ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# django-tenants migrates SHARED_APPS to public and TENANT_APPS to tenant schemas.
SHARED_APPS = [
    "django_tenants",
    "apps.tenancy",
    "apps.marketplace",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "django_htmx",
    "modeltranslation",
    "apps.core",
]

TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "django_htmx",
    "modeltranslation",
    "django_celery_beat",
    "apps.identity",
    "apps.locations",
    "apps.plants",
    "apps.pots",
    "apps.devices",
    "apps.telemetry",
    "apps.care_engine",
    "apps.integrations",
    "apps.provider_ops",
    "apps.notifications",
    "apps.billing",
    "apps.audit",
]

GIS_ENABLED = env.bool("DJANGO_GIS_ENABLED", default=False)
if GIS_ENABLED:
    TENANT_APPS.insert(5, "django.contrib.gis")

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "tenancy.Client"
TENANT_DOMAIN_MODEL = "tenancy.Domain"
PUBLIC_SCHEMA_NAME = "public"
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.request_context.RequestContextMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env.str("POSTGRES_DB", default="flower"),
        "USER": env.str("POSTGRES_USER", default="flower"),
        "PASSWORD": env.str("POSTGRES_PASSWORD", default="flower"),
        "HOST": env.str("POSTGRES_HOST", default="localhost"),
        "PORT": env.str("POSTGRES_PORT", default="5432"),
        "OPTIONS": {
            "connect_timeout": env.int("POSTGRES_CONNECT_TIMEOUT", default=5),
        },
    }
}

AUTH_USER_MODEL = "identity.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "sr"
TIME_ZONE = "Europe/Belgrade"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("sr", "Serbian"),
    ("en", "English"),
    ("hr", "Croatian"),
    ("sl", "Slovenian"),
    ("mk", "Macedonian"),
    ("sq", "Albanian"),
    ("el", "Greek"),
    ("de", "German"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

MODELTRANSLATION_DEFAULT_LANGUAGE = "sr"
MODELTRANSLATION_LANGUAGES = ("sr", "en", "hr", "sl", "mk", "sq", "el", "de")
MODELTRANSLATION_FALLBACK_LANGUAGES = {"default": ("sr", "en")}

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Flower API",
    "DESCRIPTION": "Multi-tenant SaaS API for plant care, IoT monitoring, provider operations, and marketplace workflows.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/",
}

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

MQTT_HOST = env.str("MQTT_HOST", default="localhost")
MQTT_PORT = env.int("MQTT_PORT", default=1883)
B2B_TEST_API_KEY = env.str("B2B_TEST_API_KEY", default="test-provider-api-key")
B2B_HTTP_TIMEOUT_SECONDS = env.float("B2B_HTTP_TIMEOUT_SECONDS", default=5.0)
B2B_HMAC_MAX_SKEW_SECONDS = env.int("B2B_HMAC_MAX_SKEW_SECONDS", default=300)
B2B_TEST_KEY_ID = env.str("B2B_TEST_KEY_ID", default="test-key-id")
B2B_TEST_SECRET_REFERENCE = env.str(
    "B2B_TEST_SECRET_REFERENCE",
    default="settings://b2b/test-shared-secret",
)
B2B_TEST_SHARED_SECRET = env.str("B2B_TEST_SHARED_SECRET", default="test-shared-secret")
B2B_TEST_SECRETS = {B2B_TEST_SECRET_REFERENCE: B2B_TEST_SHARED_SECRET}
B2B_TEST_KEY_STATUS = env.str("B2B_TEST_KEY_STATUS", default="active")
B2B_TEST_KEY_VALID_FROM = env.str("B2B_TEST_KEY_VALID_FROM", default="")
B2B_TEST_KEY_VALID_UNTIL = env.str("B2B_TEST_KEY_VALID_UNTIL", default="")

EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@flower.local")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
