"""Test settings."""

import os

# Ensure a key is set before base settings import.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("DJANGO_DEBUG", "False")

from config.settings.base import *  # noqa: F403

DEBUG = False

SECRET_KEY = "test-secret-key-not-for-production"

ALLOWED_HOSTS = ["localhost", "testserver"]

# ---------------------------------------------------------------------------
# Use in-memory database for fast tests, or same Postgres with test db
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": env.str("POSTGRES_DB", default="flower") + "_test",  # noqa: F405
        "USER": env.str("POSTGRES_USER", default="flower"),  # noqa: F405
        "PASSWORD": env.str("POSTGRES_PASSWORD", default="flower"),  # noqa: F405
        "HOST": env.str("POSTGRES_HOST", default="localhost"),  # noqa: F405
        "PORT": env.str("POSTGRES_PORT", default="5432"),  # noqa: F405
        "OPTIONS": {
            "connect_timeout": env.int("POSTGRES_CONNECT_TIMEOUT", default=2),  # noqa: F405
        },
    }
}

# ---------------------------------------------------------------------------
# Speed up tests
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# ---------------------------------------------------------------------------
# Disable Celery in tests
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Disable logging noise during tests
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
}

# ---------------------------------------------------------------------------
# Media storage in tests
# ---------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "django.core.files.storage.InMemoryStorage"
