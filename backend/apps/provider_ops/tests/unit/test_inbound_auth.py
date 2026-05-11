"""Unit tests for provider inbound authentication with ProviderInboundKey (Phase 8)."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from rest_framework import exceptions
from rest_framework.test import APIRequestFactory

from apps.provider_ops.api.authentication import (
    B2BProviderAuthentication,
    _resolve_required_scope,
)
from apps.provider_ops.domain.enums import InboundKeyStatus
from apps.provider_ops.services.inbound_key_service import (
    InboundKeyUnavailable,
)


# ---------------------------------------------------------------------------
# _resolve_required_scope
# ---------------------------------------------------------------------------


def test_resolve_location_scope():
    assert _resolve_required_scope("/api/b2b/v1/locations/upsert/") == "locations:write"


def test_resolve_device_scope():
    assert _resolve_required_scope("/api/b2b/v1/devices/upsert/") == "devices:write"


def test_resolve_telemetry_scope():
    assert _resolve_required_scope("/api/b2b/v1/telemetry/batch/") == "telemetry:write"


def test_resolve_unknown_scope():
    assert _resolve_required_scope("/api/b2b/v1/sync/status/") is None


# ---------------------------------------------------------------------------
# _authenticate_hmac — registry lookup
# ---------------------------------------------------------------------------


def _make_request(path="/api/b2b/v1/locations/upsert/", key_id="test-key"):
    factory = APIRequestFactory()
    return factory.post(
        path,
        {"source_owner_tenant_id": "owner-1", "external_id": "loc-1", "name": "Office"},
        format="json",
        HTTP_X_B2B_KEY_ID=key_id,
        HTTP_X_B2B_TIMESTAMP="1234567890",
        HTTP_X_B2B_SIGNATURE="abc",
        HTTP_X_IDEMPOTENCY_KEY="idem-1",
    )


def test_active_inbound_key_authenticates(monkeypatch):
    """active inbound key + valid HMAC + valid scope = authenticated."""
    request = _make_request()

    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.get_active_inbound_key",
        lambda **kwargs: SimpleNamespace(
            key_id="test-key",
            status=InboundKeyStatus.ACTIVE,
            secret_reference="ref://key",
            source_owner_tenant_id="owner-1",
            scopes=["locations:write"],
        ),
    )
    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.resolve_secret",
        lambda *args, **kwargs: "shared-secret",
    )
    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.verify_hmac_signature",
        lambda **kwargs: None,
    )

    principal, _ = B2BProviderAuthentication().authenticate(request)
    assert principal.is_authenticated is True
    assert request.b2b_source_owner_tenant_id == "owner-1"


def test_revoked_inbound_key_is_rejected(monkeypatch):
    """revoked inbound key raises AuthenticationFailed."""
    request = _make_request()

    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.get_active_inbound_key",
        MagicMock(side_effect=InboundKeyUnavailable("Inbound key is revoked.")),
    )

    with pytest.raises(exceptions.AuthenticationFailed):
        B2BProviderAuthentication().authenticate(request)


def test_expired_inbound_key_is_rejected(monkeypatch):
    """expired inbound key raises AuthenticationFailed."""
    request = _make_request()

    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.get_active_inbound_key",
        MagicMock(side_effect=InboundKeyUnavailable("Inbound key is expired.")),
    )

    with pytest.raises(exceptions.AuthenticationFailed):
        B2BProviderAuthentication().authenticate(request)


def test_unknown_key_id_is_rejected(monkeypatch):
    """unknown key_id raises AuthenticationFailed."""
    request = _make_request(key_id="unknown")

    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.get_active_inbound_key",
        MagicMock(side_effect=InboundKeyUnavailable("Inbound key is unknown.")),
    )

    with pytest.raises(exceptions.AuthenticationFailed):
        B2BProviderAuthentication().authenticate(request)


def test_key_without_required_scope_is_rejected(monkeypatch):
    """key without required scope raises AuthenticationFailed."""
    request = _make_request()

    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.get_active_inbound_key",
        lambda **kwargs: SimpleNamespace(
            key_id="test-key",
            status=InboundKeyStatus.ACTIVE,
            secret_reference="ref://key",
            source_owner_tenant_id="owner-1",
            scopes=["telemetry:write"],  # does NOT include locations:write
        ),
    )
    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.resolve_secret",
        lambda *args, **kwargs: "shared-secret",
    )
    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.verify_hmac_signature",
        lambda **kwargs: None,
    )

    with pytest.raises(exceptions.AuthenticationFailed):
        B2BProviderAuthentication().authenticate(request)


def test_missing_key_id_header_is_rejected():
    """missing X-B2B-Key-Id raises AuthenticationFailed."""
    factory = APIRequestFactory()
    request = factory.post(
        "/api/b2b/v1/locations/upsert/",
        {"source_owner_tenant_id": "owner-1", "external_id": "loc-1"},
        format="json",
        HTTP_X_B2B_TIMESTAMP="1234567890",
        HTTP_X_B2B_SIGNATURE="abc",
        HTTP_X_IDEMPOTENCY_KEY="idem-1",
    )

    with pytest.raises(exceptions.AuthenticationFailed, match="X-B2B-Key-Id"):
        B2BProviderAuthentication().authenticate(request)


# ---------------------------------------------------------------------------
# Settings fallback (test mode)
# ---------------------------------------------------------------------------


@override_settings(B2B_USE_SETTINGS_KEY=True)
def test_settings_fallback_works_in_test_mode(monkeypatch):
    """settings fallback authenticates when B2B_USE_SETTINGS_KEY is True."""
    request = _make_request()

    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.get_active_inbound_key",
        lambda **kwargs: SimpleNamespace(
            key_id="test-key",
            status=InboundKeyStatus.ACTIVE,
            secret_reference="ref://settings",
            source_owner_tenant_id="owner-settings",
            scopes=["locations:write"],
        ),
    )
    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.resolve_secret",
        lambda *args, **kwargs: "shared-secret",
    )
    monkeypatch.setattr(
        "apps.provider_ops.api.authentication.verify_hmac_signature",
        lambda **kwargs: None,
    )

    principal, _ = B2BProviderAuthentication().authenticate(request)
    assert principal.is_authenticated is True


# ---------------------------------------------------------------------------
# test API key still works
# ---------------------------------------------------------------------------


@override_settings(B2B_TEST_API_KEY="test-api-key")
def test_test_api_key_authenticates():
    factory = APIRequestFactory()
    request = factory.post(
        "/api/b2b/v1/locations/upsert/",
        {"source_owner_tenant_id": "owner-1", "external_id": "loc-1"},
        format="json",
        HTTP_X_PROVIDER_API_KEY="test-api-key",
        HTTP_X_IDEMPOTENCY_KEY="idem-1",
    )

    principal, _ = B2BProviderAuthentication().authenticate(request)
    assert principal.is_authenticated is True
