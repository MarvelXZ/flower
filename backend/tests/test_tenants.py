"""
Tests for the tenants bounded context.
"""

import pytest

from apps.tenants.models import Client, Domain
from apps.tenants.services import create_tenant, deactivate_tenant


@pytest.mark.django_db
def test_client_model_exists():
    """Verify that the Client model is reachable."""
    assert Client is not None
    assert Domain is not None


@pytest.mark.django_db
def test_create_tenant_service():
    """Verify the create_tenant service works."""
    tenant = create_tenant(
        name="Test Corp",
        slug="testcorp",
        schema_name="testcorp",
        domain="testcorp.localhost",
    )
    assert tenant.name == "Test Corp"
    assert tenant.slug == "testcorp"
    assert tenant.schema_name == "testcorp"
    assert tenant.is_active is True

    domain = Domain.objects.filter(tenant=tenant).first()
    assert domain is not None
    assert domain.domain == "testcorp.localhost"
    assert domain.is_primary is True


@pytest.mark.django_db
def test_deactivate_tenant_service():
    """Verify the deactivate_tenant service works."""
    tenant = create_tenant(
        name="Inactive Corp",
        slug="inactive",
        schema_name="inactive",
        domain="inactive.localhost",
    )
    deactivate_tenant(tenant=tenant)

    tenant.refresh_from_db()
    assert tenant.is_active is False
