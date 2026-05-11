"""Pytest fixtures for Flower."""

import pytest
from django_tenants.utils import tenant_context

from apps.identity.models import User
from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client, Domain


@pytest.fixture
def public_tenant(db):
    tenant, _ = Client.objects.get_or_create(
        schema_name="public",
        defaults={
            "name": "Public",
            "slug": "public",
            "kind": TenantKind.MARKETPLACE_ADMIN,
        },
    )
    Domain.objects.get_or_create(
        tenant=tenant,
        domain="localhost",
        defaults={"is_primary": True},
    )
    return tenant


@pytest.fixture
def owner_tenant(db):
    tenant = Client.objects.create(
        name="Demo Owner",
        slug="demo-owner",
        schema_name="demo_owner",
        kind=TenantKind.OWNER,
    )
    Domain.objects.create(tenant=tenant, domain="owner.localhost", is_primary=True)
    return tenant


@pytest.fixture
def use_owner_context(owner_tenant):
    with tenant_context(owner_tenant):
        yield owner_tenant


@pytest.fixture
def tenant_user(use_owner_context):
    return User.objects.create_user(
        username="owner-user",
        email="owner@example.test",
        password="testpass123",
    )
