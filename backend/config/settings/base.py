"""
PlantOps SaaS — Base Django Settings

This module contains all shared settings. Environment-specific overrides live in
local.py, production.py, and test.py.

Architecture notes:
- Multi-tenancy via django-tenants (PostgreSQL schemas).
- DDD-friendly app layout: each app is a bounded context.
- All secrets loaded from environment variables.
- Fail-closed tenant isolation by default.
"""

from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from environs import Env

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = Env()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env.str("SECRET_KEY", default="")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "The SECRET_KEY environment variable must be set. "
        "It should be a secure random string of at least 50 characters."
    )

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[], subcast=str)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[], subcast=str)

# ---------------------------------------------------------------------------
# Application Definition
# ---------------------------------------------------------------------------
# django-tenants splits apps into SHARED_APPS (public schema) and
# TENANT_APPS (tenant schemas). Only apps listed here are migrated.

SHARED_APPS = [
    # django-tenants must come before django.contrib.contenttypes
    "django_tenants",
    # Django core
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    # Third-party shared
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "django_htmx",
    "modeltranslation",
    "django_celery_beat",
    # PlantOps shared apps
    "apps.core",
    "apps.tenants",
]

TENANT_APPS = [
    # Django core (required in tenant schemas)
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.admin",
    # Third-party tenant
    "rest_framework",
    "drf_spectacular",
    "django_htmx",
    "modeltranslation",
    "django_celery_beat",
    # PlantOps bounded contexts
    "apps.users",
    "apps.locations",
    "apps.planters",
    "apps.plants",
    "apps.devices",
    "apps.telemetry",
    "apps.alerts",
    "apps.automation",
    "apps.firmware",
    "apps.tasks",
    "apps.notifications",
    "apps.billing",
    "apps.audit",
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

# ---------------------------------------------------------------------------
# Tenant Configuration
# ---------------------------------------------------------------------------
TENANT_MODEL = "tenants.Client"
TENANT_DOMAIN_MODEL = "tenants.Domain"

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

# ---------------------------------------------------------------------------
# URL Configuration
# ---------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"

# ---------------------------------------------------------------------------
# Template Configuration
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# WSGI / ASGI
# ---------------------------------------------------------------------------
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env.str("POSTGRES_DB", default="plantops"),
        "USER": env.str("POSTGRES_USER", default="plantops"),
        "PASSWORD": env.str("POSTGRES_PASSWORD", default="plantops"),
        "HOST": env.str("POSTGRES_HOST", default="localhost"),
        "PORT": env.str("POSTGRES_PORT", default="5432"),
    }
}

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "users.User"

# ---------------------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "sr"
TIME_ZONE = "Europe/Belgrade"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("sr", "Srpski"),
    ("en", "English"),
    ("hr", "Hrvatski"),
    ("sl", "Slovenščina"),
    ("mk", "Македонски"),
    ("sq", "Shqip"),
    ("el", "Ελληνικά"),
    ("de", "Deutsch"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# ---------------------------------------------------------------------------
# Model Translation
# ---------------------------------------------------------------------------
MODELTRANSLATION_DEFAULT_LANGUAGE = "sr"
MODELTRANSLATION_LANGUAGES = ("sr", "en", "hr", "sl", "mk", "sq", "el", "de")
MODELTRANSLATION_FALLBACK_LANGUAGES = {"default": ("sr", "en")}

# ---------------------------------------------------------------------------
# Static & Media Files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default Primary Key Field Type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
}

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI schema)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "PlantOps API",
    "DESCRIPTION": "Multi-tenant SaaS API for IoT plant and planter management.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[], subcast=str)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="amqp://guest:guest@localhost:5672//")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env.str("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="noreply@plantops.local")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Security Defaults
# ---------------------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# These are intentionally left for environment-specific settings:
# SECURE_SSL_REDIRECT, SECURE_HSTS_SECONDS, SESSION_COOKIE_SECURE, etc.
