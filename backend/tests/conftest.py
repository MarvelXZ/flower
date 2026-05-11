"""
Pytest fixtures and configuration.
"""

import pytest
from django_tenants.utils import tenant_context

from apps.tenants.models import Client, Domain
from apps.users.models import User


@pytest.fixture
def public_tenant(db):
    """Create a public schema tenant for shared-app tests."""
    tenant, _ = Client.objects.get_or_create(
        schema_name="public",
        defaults={
            "name": "Public",
            "slug": "public",
        },
    )
    Domain.objects.get_or_create(
        tenant=tenant,
        domain="localhost",
        defaults={"is_primary": True},
    )
    return tenant


@pytest.fixture
def demo_tenant(db):
    """Create a demo tenant with its own schema."""
    tenant = Client.objects.create(
        name="Demo Tenant",
        slug="demo",
        schema_name="demo",
    )
    Domain.objects.create(
        tenant=tenant,
        domain="demo.localhost",
        is_primary=True,
    )
    return tenant


@pytest.fixture
def use_tenant_context(demo_tenant):
    """Fixture to run code inside a tenant context."""
    with tenant_context(demo_tenant):
        yield demo_tenant


@pytest.fixture
def tenant_user(use_tenant_context):
    """Create a regular user within the demo tenant context."""
    return User.objects.create_user(
        username="testgardener",
        email="gardener@demo.local",
        password="testpass123",
        role="gardener",
    )


@pytest.fixture
def admin_user(use_tenant_context):
    """Create an admin user within the demo tenant context."""
    return User.objects.create_user(
        username="testadmin",
        email="admin@demo.local",
        password="testpass123",
        role="admin",
        is_staff=True,
    )
