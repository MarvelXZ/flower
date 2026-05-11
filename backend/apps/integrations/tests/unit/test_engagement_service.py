"""Unit tests for ProviderEngagement lifecycle (Phase 8)."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.integrations.domain.enums import EngagementStatus
from apps.integrations.services.engagement_service import (
    InvalidEngagementTransition,
    _validate_transition,
    activate_engagement,
    create_engagement,
    get_active_engagement,
    revoke_engagement,
    suspend_engagement,
)


def _mock_atomic(monkeypatch):
    """Mock transaction.atomic to avoid database access in unit tests."""
    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.transaction.atomic",
        lambda: nullcontext(),
    )


# ---------------------------------------------------------------------------
# _validate_transition
# ---------------------------------------------------------------------------


def test_pending_to_active_is_allowed():
    _validate_transition(EngagementStatus.PENDING, EngagementStatus.ACTIVE)  # no raise


def test_pending_to_revoked_is_allowed():
    _validate_transition(EngagementStatus.PENDING, EngagementStatus.REVOKED)  # no raise


def test_active_to_suspended_is_allowed():
    _validate_transition(EngagementStatus.ACTIVE, EngagementStatus.SUSPENDED)  # no raise


def test_active_to_revoked_is_allowed():
    _validate_transition(EngagementStatus.ACTIVE, EngagementStatus.REVOKED)  # no raise


def test_suspended_to_active_is_allowed():
    _validate_transition(EngagementStatus.SUSPENDED, EngagementStatus.ACTIVE)  # no raise


def test_suspended_to_revoked_is_allowed():
    _validate_transition(EngagementStatus.SUSPENDED, EngagementStatus.REVOKED)  # no raise


def test_revoked_to_anything_is_denied():
    for target in EngagementStatus.values:
        if target == EngagementStatus.REVOKED:
            continue
        with pytest.raises(InvalidEngagementTransition):
            _validate_transition(EngagementStatus.REVOKED, target)


def test_pending_to_suspended_is_denied():
    with pytest.raises(InvalidEngagementTransition):
        _validate_transition(EngagementStatus.PENDING, EngagementStatus.SUSPENDED)


def test_active_to_pending_is_denied():
    with pytest.raises(InvalidEngagementTransition):
        _validate_transition(EngagementStatus.ACTIVE, EngagementStatus.PENDING)


# ---------------------------------------------------------------------------
# create_engagement
# ---------------------------------------------------------------------------


def test_create_engagement_returns_pending(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    SimpleNamespace(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
        status=EngagementStatus.PENDING,
        scopes=[],
        created_at=now,
        activated_at=None,
        suspended_at=None,
        revoked_at=None,
    )

    class FakeModel:
        class objects:
            @staticmethod
            def create(**kwargs):
                return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.ProviderEngagement",
        FakeModel,
    )

    engagement = create_engagement(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
        scopes=["telemetry:write"],
    )
    assert engagement.status == EngagementStatus.PENDING
    assert engagement.owner_tenant_id == "owner-1"
    assert engagement.provider_tenant_id == "provider-1"


# ---------------------------------------------------------------------------
# activate_engagement
# ---------------------------------------------------------------------------


def test_activate_pending_engagement_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    fake = MagicMock()
    fake.status = EngagementStatus.PENDING

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    result = activate_engagement(engagement=fake)
    assert result.status == EngagementStatus.ACTIVE
    assert result.activated_at == now


def test_activate_revoked_engagement_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = EngagementStatus.REVOKED

    with pytest.raises(InvalidEngagementTransition):
        activate_engagement(engagement=fake)


# ---------------------------------------------------------------------------
# suspend_engagement
# ---------------------------------------------------------------------------


def test_suspend_active_engagement_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    fake = MagicMock()
    fake.status = EngagementStatus.ACTIVE

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    result = suspend_engagement(engagement=fake)
    assert result.status == EngagementStatus.SUSPENDED
    assert result.suspended_at == now


def test_suspend_pending_engagement_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = EngagementStatus.PENDING

    with pytest.raises(InvalidEngagementTransition):
        suspend_engagement(engagement=fake)


# ---------------------------------------------------------------------------
# revoke_engagement
# ---------------------------------------------------------------------------


def test_revoke_active_engagement_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    fake = MagicMock()
    fake.status = EngagementStatus.ACTIVE

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    result = revoke_engagement(engagement=fake)
    assert result.status == EngagementStatus.REVOKED
    assert result.revoked_at == now


def test_revoke_revoked_engagement_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = EngagementStatus.REVOKED

    with pytest.raises(InvalidEngagementTransition):
        revoke_engagement(engagement=fake)


# ---------------------------------------------------------------------------
# get_active_engagement
# ---------------------------------------------------------------------------


def test_get_active_engagement_found(monkeypatch):
    fake_engagement = SimpleNamespace(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
        status=EngagementStatus.ACTIVE,
    )

    class FakeQuerySet:
        @staticmethod
        def get(**kwargs):
            if (
                kwargs.get("owner_tenant_id") == "owner-1"
                and kwargs.get("provider_tenant_id") == "provider-1"
                and kwargs.get("status") == EngagementStatus.ACTIVE
            ):
                return fake_engagement
            raise SimpleNamespace(
                __class__=type("DoesNotExist", (), {})
            )

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.ProviderEngagement",
        SimpleNamespace(objects=FakeQuerySet()),
    )

    result = get_active_engagement(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
    )
    assert result is not None
    assert result.status == EngagementStatus.ACTIVE


def test_get_active_engagement_not_found(monkeypatch):
    class NotFoundError(Exception):
        pass

    class FakeModel:
        objects = SimpleNamespace(
            get=MagicMock(side_effect=NotFoundError())
        )
    FakeModel.DoesNotExist = NotFoundError

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.ProviderEngagement",
        FakeModel,
    )

    result = get_active_engagement(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
    )
    assert result is None
