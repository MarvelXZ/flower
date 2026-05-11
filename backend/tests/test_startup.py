"""Basic startup tests."""

from django.conf import settings


def test_django_settings_are_loaded():
    assert settings.DATABASES["default"]["ENGINE"] == "django_tenants.postgresql_backend"
    assert settings.TENANT_MODEL == "tenancy.Client"
    assert settings.TENANT_DOMAIN_MODEL == "tenancy.Domain"


def test_required_bounded_contexts_are_installed():
    expected_apps = {
        "apps.tenancy",
        "apps.identity",
        "apps.locations",
        "apps.plants",
        "apps.pots",
        "apps.devices",
        "apps.telemetry",
        "apps.care_engine",
        "apps.integrations",
        "apps.provider_ops",
        "apps.marketplace",
        "apps.notifications",
        "apps.billing",
        "apps.audit",
    }

    assert expected_apps.issubset(set(settings.INSTALLED_APPS))
