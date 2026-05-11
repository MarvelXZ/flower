"""Foundation tests for django-tenants setup."""

import importlib
import pkgutil

from django.conf import settings
from django_tenants.models import DomainMixin, TenantMixin

from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.management.commands.create_demo_tenants import DEMO_TENANTS
from apps.tenancy.models import Client, Domain


def test_tenant_kind_contains_required_values():
    assert set(TenantKind.values) == {
        "owner",
        "provider",
        "hybrid",
        "marketplace_admin",
    }


def test_client_accepts_all_tenant_kinds_without_database_write():
    for kind in TenantKind.values:
        tenant = Client(
            name=f"Tenant {kind}",
            slug=f"tenant-{kind}",
            schema_name=f"tenant_{kind}",
            kind=kind,
        )
        assert tenant.kind == kind


def test_client_and_domain_are_django_tenants_compatible():
    assert settings.TENANT_MODEL == "tenancy.Client"
    assert settings.TENANT_DOMAIN_MODEL == "tenancy.Domain"
    assert issubclass(Client, TenantMixin)
    assert issubclass(Domain, DomainMixin)


def test_domain_belongs_to_tenant_without_database_write():
    tenant = Client(name="Owner", slug="owner", schema_name="owner", kind=TenantKind.OWNER)
    domain = Domain(domain="owner.localhost", tenant=tenant, is_primary=True)

    assert domain.tenant is tenant
    assert domain.domain == "owner.localhost"
    assert domain.is_primary is True


def test_demo_tenant_bootstrap_definitions_cover_required_tenants():
    definitions = {tenant.kind: tenant for tenant in DEMO_TENANTS}

    assert definitions[TenantKind.OWNER].domain == "owner.localhost"
    assert definitions[TenantKind.PROVIDER].domain == "provider.localhost"
    assert definitions[TenantKind.HYBRID].domain == "hybrid.localhost"


def test_initial_migrations_are_importable():
    migration_packages = [
        "apps.audit.migrations",
        "apps.care_engine.migrations",
        "apps.devices.migrations",
        "apps.identity.migrations",
        "apps.integrations.migrations",
        "apps.locations.migrations",
        "apps.marketplace.migrations",
        "apps.notifications.migrations",
        "apps.plants.migrations",
        "apps.provider_ops.migrations",
        "apps.telemetry.migrations",
        "apps.tenancy.migrations",
    ]

    for package_name in migration_packages:
        package = importlib.import_module(package_name)
        migration_modules = [
            module.name
            for module in pkgutil.iter_modules(package.__path__)
            if module.name != "__init__"
        ]
        assert migration_modules
        for module_name in migration_modules:
            assert importlib.import_module(f"{package_name}.{module_name}")
