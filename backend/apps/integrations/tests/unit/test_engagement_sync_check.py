"""Unit tests for engagement-based sync gating (Phase 8).

These tests verify that engagement status controls whether a provider
can send or receive synchronised data.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock


from apps.integrations.domain.enums import EngagementStatus
from apps.integrations.services.engagement_service import (
    get_active_engagement,
)


def test_active_engagement_allows_sync(monkeypatch):
    """An active engagement returns the engagement object."""
    fake = SimpleNamespace(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
        status=EngagementStatus.ACTIVE,
    )

    class FakeModel:
        class DoesNotExist(Exception):
            pass
        objects = SimpleNamespace(
            get=MagicMock(return_value=fake)
        )

    monkeypatch.setattr(
        "apps.integrations.services.engagement_service.ProviderEngagement",
        FakeModel,
    )

    result = get_active_engagement(
        owner_tenant_id="owner-1",
        provider_tenant_id="provider-1",
    )
    assert result is not None
    assert result.status == EngagementStatus.ACTIVE


def test_revoked_engagement_blocks_sync(monkeypatch):
    """A revoked engagement does not return the engagement object."""
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


def test_pending_engagement_blocks_sync(monkeypatch):
    """A pending engagement does not return the engagement object."""
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


def test_suspended_engagement_blocks_sync(monkeypatch):
    """A suspended engagement does not return the engagement object."""
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
