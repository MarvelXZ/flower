"""Unit tests for provider inbound key registry (Phase 8)."""

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.provider_ops.domain.enums import InboundKeyStatus
from apps.provider_ops.services.inbound_key_service import (
    InboundKeyScopeError,
    InboundKeyUnavailable,
    _is_inbound_key_usable,
    _key_has_scope,
    get_active_inbound_key,
    get_settings_inbound_key,
    validate_inbound_key_scope,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_key(
    *,
    key_id="test-key",
    status=InboundKeyStatus.ACTIVE,
    valid_from=None,
    valid_until=None,
    scopes=None,
):
    return SimpleNamespace(
        key_id=key_id,
        status=status,
        valid_from=valid_from,
        valid_until=valid_until,
        scopes=scopes or [],
        source_owner_tenant_id="owner-1",
    )


# ---------------------------------------------------------------------------
# _is_inbound_key_usable
# ---------------------------------------------------------------------------


def test_active_key_is_usable():
    now = timezone.now()
    key = _make_key(valid_from=now - timedelta(hours=1))
    assert _is_inbound_key_usable(key, now=now) is True


def test_disabled_key_is_not_usable():
    now = timezone.now()
    key = _make_key(status=InboundKeyStatus.DISABLED, valid_from=now - timedelta(hours=1))
    assert _is_inbound_key_usable(key, now=now) is False


def test_revoked_key_is_not_usable():
    now = timezone.now()
    key = _make_key(status=InboundKeyStatus.REVOKED, valid_from=now - timedelta(hours=1))
    assert _is_inbound_key_usable(key, now=now) is False


def test_expired_key_is_not_usable():
    now = timezone.now()
    key = _make_key(
        valid_from=now - timedelta(days=2),
        valid_until=now - timedelta(days=1),
    )
    assert _is_inbound_key_usable(key, now=now) is False


def test_future_key_is_not_usable():
    now = timezone.now()
    key = _make_key(valid_from=now + timedelta(hours=1))
    assert _is_inbound_key_usable(key, now=now) is False


# ---------------------------------------------------------------------------
# _key_has_scope
# ---------------------------------------------------------------------------


def test_key_with_required_scope_allows():
    key = _make_key(scopes=["telemetry:write", "locations:write"])
    assert _key_has_scope(key, required_scope="telemetry:write") is True


def test_key_without_required_scope_denies():
    key = _make_key(scopes=["locations:write"])
    assert _key_has_scope(key, required_scope="telemetry:write") is False


def test_key_with_empty_scopes_denies():
    key = _make_key(scopes=[])
    assert _key_has_scope(key, required_scope="telemetry:write") is False


def test_empty_required_scope_is_always_allowed():
    key = _make_key(scopes=[])
    assert _key_has_scope(key, required_scope="") is True


# ---------------------------------------------------------------------------
# validate_inbound_key_scope
# ---------------------------------------------------------------------------


def test_validate_inbound_key_scope_passes():
    key = _make_key(scopes=["telemetry:write"])
    validate_inbound_key_scope(key=key, required_scope="telemetry:write")  # no raise


def test_validate_inbound_key_scope_raises():
    key = _make_key(scopes=["locations:write"])
    with pytest.raises(InboundKeyScopeError):
        validate_inbound_key_scope(key=key, required_scope="telemetry:write")


# ---------------------------------------------------------------------------
# get_active_inbound_key — registry lookup
# ---------------------------------------------------------------------------


def test_get_active_inbound_key_found(monkeypatch):
    now = timezone.now()
    fake_key = SimpleNamespace(
        key_id="registry-key",
        status=InboundKeyStatus.ACTIVE,
        valid_from=now - timedelta(hours=1),
        valid_until=None,
        scopes=["telemetry:write"],
        source_owner_tenant_id="owner-1",
        secret_reference="ref://registry",
    )

    class FakeQuerySet:
        def get(self, **kwargs):
            if kwargs.get("key_id") == "registry-key":
                return fake_key
            raise SimpleNamespace(
                __class__=type("DoesNotExist", (), {})
            )  # won't be raised

    monkeypatch.setattr(
        "apps.provider_ops.services.inbound_key_service.ProviderInboundKey",
        SimpleNamespace(objects=FakeQuerySet()),
    )

    result = get_active_inbound_key(key_id="registry-key", now=now)
    assert result.key_id == "registry-key"
    assert result.source_owner_tenant_id == "owner-1"


def test_get_active_inbound_key_not_found_raises(monkeypatch):
    now = timezone.now()

    class DoesNotExistError(Exception):
        pass

    class FakeModelWithDNE:
        DoesNotExist = DoesNotExistError

        objects = SimpleNamespace(
            get=MagicMock(side_effect=DoesNotExistError())
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.inbound_key_service.ProviderInboundKey",
        FakeModelWithDNE,
    )

    with pytest.raises(InboundKeyUnavailable):
        get_active_inbound_key(key_id="unknown-key", now=now)


def test_get_active_inbound_key_expired_raises(monkeypatch):
    now = timezone.now()
    fake_key = SimpleNamespace(
        key_id="expired-key",
        status=InboundKeyStatus.ACTIVE,
        valid_from=now - timedelta(days=2),
        valid_until=now - timedelta(days=1),
        scopes=[],
        source_owner_tenant_id="owner-1",
        secret_reference="ref://expired",
    )

    class FakeModel:
        class DoesNotExist(Exception):
            pass

        objects = SimpleNamespace(
            get=MagicMock(return_value=fake_key)
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.inbound_key_service.ProviderInboundKey",
        FakeModel,
    )

    with pytest.raises(InboundKeyUnavailable, match="expired"):
        get_active_inbound_key(key_id="expired-key", now=now)


# ---------------------------------------------------------------------------
# get_settings_inbound_key — settings fallback (test mode)
# ---------------------------------------------------------------------------


@override_settings(
    B2B_TEST_KEY_ID="settings-key",
    B2B_TEST_SECRET_REFERENCE="ref://settings",
    B2B_TEST_SOURCE_OWNER_TENANT_ID="owner-settings",
    B2B_TEST_KEY_STATUS=InboundKeyStatus.ACTIVE,
    B2B_TEST_KEY_VALID_FROM=None,
    B2B_TEST_KEY_VALID_UNTIL=None,
    B2B_TEST_KEY_SCOPES=["telemetry:write"],
)
def test_get_settings_inbound_key_active():
    now = timezone.now()
    key = get_settings_inbound_key(key_id="settings-key", now=now)
    assert key.key_id == "settings-key"
    assert key.source_owner_tenant_id == "owner-settings"
    assert key.status == InboundKeyStatus.ACTIVE


@override_settings(
    B2B_TEST_KEY_ID="settings-key",
    B2B_TEST_KEY_STATUS=InboundKeyStatus.REVOKED,
)
def test_get_settings_inbound_key_revoked_raises():
    now = timezone.now()
    with pytest.raises(InboundKeyUnavailable):
        get_settings_inbound_key(key_id="settings-key", now=now)


@override_settings(B2B_TEST_KEY_ID="settings-key")
def test_get_settings_inbound_key_unknown_key_id_raises():
    now = timezone.now()
    with pytest.raises(InboundKeyUnavailable):
        get_settings_inbound_key(key_id="wrong-key", now=now)
