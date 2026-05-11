"""Phase 7 tests for provider key lifecycle and secret resolution."""

from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.integrations.domain.enums import ProviderKeyStatus
from apps.integrations.services import provider_key_service
from apps.integrations.services.secret_resolver import InMemorySecretResolver, SettingsSecretResolver


class FakeProviderKey:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.saved_update_fields = None

    def save(self, *, update_fields):
        self.saved_update_fields = list(update_fields)


class FakeProviderKeyManager:
    def __init__(self):
        self.created = []

    def create(self, **kwargs):
        key = FakeProviderKey(**kwargs)
        self.created.append(key)
        return key


class FakeProviderKeyModel:
    objects = FakeProviderKeyManager()


def _patch_key_model(monkeypatch):
    FakeProviderKeyModel.objects = FakeProviderKeyManager()
    monkeypatch.setattr(provider_key_service, "ProviderKey", FakeProviderKeyModel)
    monkeypatch.setattr(provider_key_service.transaction, "atomic", lambda: nullcontext())
    return FakeProviderKeyModel.objects


def test_settings_secret_resolver_returns_secret():
    with override_settings(
        B2B_TEST_SECRET_REFERENCE="settings://provider/key-1",
        B2B_TEST_SHARED_SECRET="resolved-secret",
        B2B_TEST_SECRETS={},
    ):
        assert SettingsSecretResolver().resolve_secret("settings://provider/key-1") == "resolved-secret"


def test_in_memory_secret_resolver_returns_secret():
    resolver = InMemorySecretResolver({"secret://provider/key-1": "resolved-secret"})

    assert resolver.resolve_secret("secret://provider/key-1") == "resolved-secret"


def test_create_provider_key_uses_service_layer_and_audit(monkeypatch):
    manager = _patch_key_model(monkeypatch)
    connection = SimpleNamespace(id=1)
    audited = []

    monkeypatch.setattr(
        provider_key_service,
        "get_active_key_for_connection",
        lambda *, provider_connection, now=None: (_ for _ in ()).throw(provider_key_service.ProviderKeyUnavailable()),
    )
    monkeypatch.setattr(provider_key_service, "audit_integration_event", lambda **kwargs: audited.append(kwargs))

    key = provider_key_service.create_provider_key(
        provider_connection=connection,
        key_id="key-1",
        secret_reference="secret://provider/key-1",
    )

    assert key.status == ProviderKeyStatus.ACTIVE
    assert key.secret_reference == "secret://provider/key-1"
    assert manager.created == [key]
    assert audited[0]["event_type"] == "key_created"


def test_create_provider_key_rejects_existing_active_key(monkeypatch):
    _patch_key_model(monkeypatch)
    connection = SimpleNamespace(id=1)
    existing = FakeProviderKey(key_id="key-1", status=ProviderKeyStatus.ACTIVE)

    monkeypatch.setattr(
        provider_key_service,
        "get_active_key_for_connection",
        lambda *, provider_connection, now=None: existing,
    )

    with pytest.raises(provider_key_service.ProviderKeyLifecycleError):
        provider_key_service.create_provider_key(
            provider_connection=connection,
            key_id="key-2",
            secret_reference="secret://provider/key-2",
        )


def test_rotate_provider_key_creates_new_active_and_rotates_old(monkeypatch):
    manager = _patch_key_model(monkeypatch)
    connection = SimpleNamespace(id=1)
    old_key = FakeProviderKey(
        provider_connection=connection,
        key_id="key-1",
        status=ProviderKeyStatus.ACTIVE,
        valid_until=None,
        rotated_at=None,
    )
    audited = []

    monkeypatch.setattr(
        provider_key_service,
        "get_active_key_for_connection",
        lambda *, provider_connection, now=None: old_key,
    )
    monkeypatch.setattr(provider_key_service, "audit_integration_event", lambda **kwargs: audited.append(kwargs))

    new_key = provider_key_service.rotate_provider_key(
        provider_connection=connection,
        new_key_id="key-2",
        new_secret_reference="secret://provider/key-2",
    )

    assert old_key.status == ProviderKeyStatus.ROTATED
    assert old_key.valid_until is not None
    assert old_key.rotated_at is not None
    assert old_key.saved_update_fields == ["status", "valid_until", "rotated_at"]
    assert new_key.status == ProviderKeyStatus.ACTIVE
    assert new_key.key_id == "key-2"
    assert manager.created == [new_key]
    assert audited[0]["event_type"] == "key_rotated"


def test_revoke_provider_key_marks_key_revoked(monkeypatch):
    monkeypatch.setattr(provider_key_service.transaction, "atomic", lambda: nullcontext())
    monkeypatch.setattr(provider_key_service, "audit_integration_event", lambda **kwargs: None)
    connection = SimpleNamespace(id=1)
    key = FakeProviderKey(
        provider_connection=connection,
        key_id="key-1",
        status=ProviderKeyStatus.ACTIVE,
        valid_until=None,
        revoked_at=None,
    )

    provider_key_service.revoke_provider_key(provider_key=key)

    assert key.status == ProviderKeyStatus.REVOKED
    assert key.valid_until is not None
    assert key.revoked_at is not None
    assert key.saved_update_fields == ["status", "valid_until", "revoked_at"]


def test_revoked_key_is_not_usable():
    key = FakeProviderKey(
        status=ProviderKeyStatus.REVOKED,
        valid_from=timezone.now() - timedelta(minutes=1),
        valid_until=None,
    )

    assert provider_key_service.is_provider_key_usable(key) is False


def test_expired_key_is_not_usable():
    key = FakeProviderKey(
        status=ProviderKeyStatus.ACTIVE,
        valid_from=timezone.now() - timedelta(days=1),
        valid_until=timezone.now() - timedelta(seconds=1),
    )

    assert provider_key_service.is_provider_key_usable(key) is False
