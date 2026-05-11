"""Unit tests for source_owner_tenant_id validation in provider inbound (Phase 8)."""

import pytest

from apps.provider_ops.services.inbound_service import (
    SourceOwnerMismatchError,
    validate_source_owner_id,
)


def test_auth_context_overrides_payload():
    """When auth sets source_owner_tenant_id, it must match the payload."""
    result = validate_source_owner_id(
        auth_source_owner_tenant_id="owner-1",
        payload_source_owner_tenant_id="owner-1",
    )
    assert result == "owner-1"


def test_auth_context_mismatch_raises():
    """Payload source_owner_tenant_id must match the key registry binding."""
    with pytest.raises(SourceOwnerMismatchError):
        validate_source_owner_id(
            auth_source_owner_tenant_id="owner-1",
            payload_source_owner_tenant_id="owner-2",
        )


def test_no_auth_context_uses_payload():
    """Without auth context (e.g. test API key), payload value is used."""
    result = validate_source_owner_id(
        auth_source_owner_tenant_id=None,
        payload_source_owner_tenant_id="owner-1",
    )
    assert result == "owner-1"


def test_no_auth_context_empty_payload():
    """Without auth context, even an empty payload value is accepted as-is."""
    result = validate_source_owner_id(
        auth_source_owner_tenant_id=None,
        payload_source_owner_tenant_id="",
    )
    assert result == ""
