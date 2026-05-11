"""Tests for tenant classifications."""

from apps.tenancy.domain.enums import TenantKind


def test_tenant_kind_contains_required_values():
    assert TenantKind.OWNER == "owner"
    assert TenantKind.PROVIDER == "provider"
    assert TenantKind.HYBRID == "hybrid"
    assert TenantKind.MARKETPLACE_ADMIN == "marketplace_admin"
