"""Production settings."""

from config.settings.base import *  # noqa: F403

DEBUG = False

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
CONN_MAX_AGE = 60

# ---------------------------------------------------------------------------
# Static files (whitenoise or CDN in production)
# ---------------------------------------------------------------------------
MIDDLEWARE.insert(1, "django.middleware.security.SecurityMiddleware")  # noqa: F405

# ---------------------------------------------------------------------------
# Sentry (optional)
# ---------------------------------------------------------------------------
SENTRY_DSN = env.str("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
