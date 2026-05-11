"""
Basic sanity tests that Django starts up correctly.
"""

import pytest
from django.conf import settings


@pytest.mark.django_db
def test_django_settings_loaded():
    """Verify that Django settings are loaded."""
    assert settings.DEBUG is not None
    assert settings.SECRET_KEY is not None
    assert settings.DATABASES["default"]["ENGINE"] == "django_tenants.postgresql_backend"


def test_installed_apps_contains_tenants():
    """Verify that django-tenants and bounded contexts are installed."""
    assert "django_tenants" in settings.INSTALLED_APPS
    assert "apps.tenants" in settings.INSTALLED_APPS
    assert "apps.users" in settings.INSTALLED_APPS
    assert "apps.locations" in settings.INSTALLED_APPS
    assert "apps.planters" in settings.INSTALLED_APPS
    assert "apps.plants" in settings.INSTALLED_APPS
    assert "apps.devices" in settings.INSTALLED_APPS
    assert "apps.telemetry" in settings.INSTALLED_APPS
    assert "apps.alerts" in settings.INSTALLED_APPS
    assert "apps.automation" in settings.INSTALLED_APPS
    assert "apps.firmware" in settings.INSTALLED_APPS
    assert "apps.tasks" in settings.INSTALLED_APPS
    assert "apps.notifications" in settings.INSTALLED_APPS
    assert "apps.billing" in settings.INSTALLED_APPS
    assert "apps.audit" in settings.INSTALLED_APPS


def test_tenant_models_configured():
    """Verify tenant model settings."""
    assert settings.TENANT_MODEL == "tenants.Client"
    assert settings.TENANT_DOMAIN_MODEL == "tenants.Domain"
