from django.db import transaction
from django.utils import timezone

from apps.integrations.domain.enums import EngagementStatus
from apps.integrations.models import ProviderEngagement


class EngagementError(ValueError):
    """Base error for engagement lifecycle failures."""


class InvalidEngagementTransition(EngagementError):
    """Raised when a status transition is not allowed."""


class EngagementNotFound(EngagementError):
    """Raised when an engagement does not exist."""


class EngagementSyncNotAllowed(EngagementError):
    """Raised when an engagement does not allow data synchronisation."""


# ---------------------------------------------------------------------------
# Allowed status transitions
# ---------------------------------------------------------------------------
_ENGAGEMENT_TRANSITIONS: dict[str, set[str]] = {
    EngagementStatus.PENDING: {EngagementStatus.ACTIVE, EngagementStatus.REVOKED},
    EngagementStatus.ACTIVE: {EngagementStatus.SUSPENDED, EngagementStatus.REVOKED},
    EngagementStatus.SUSPENDED: {EngagementStatus.ACTIVE, EngagementStatus.REVOKED},
    EngagementStatus.REVOKED: set(),  # terminal — no outgoing transitions
}


def _validate_transition(current_status: str, target_status: str) -> None:
    allowed = _ENGAGEMENT_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidEngagementTransition(
            f"Cannot transition engagement from '{current_status}' to '{target_status}'.",
        )


# ---------------------------------------------------------------------------
# Lifecycle commands
# ---------------------------------------------------------------------------


def create_engagement(
    *,
    owner_tenant_id: str,
    provider_tenant_id: str,
    scopes: list[str] | None = None,
) -> ProviderEngagement:
    """Create a new engagement in ``pending`` status."""
    with transaction.atomic():
        engagement = ProviderEngagement.objects.create(
            owner_tenant_id=owner_tenant_id,
            provider_tenant_id=provider_tenant_id,
            status=EngagementStatus.PENDING,
            scopes=scopes or [],
        )
        return engagement


def activate_engagement(*, engagement: ProviderEngagement) -> ProviderEngagement:
    """Activate a pending or suspended engagement."""
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(engagement.status, EngagementStatus.ACTIVE)
        engagement.status = EngagementStatus.ACTIVE
        engagement.activated_at = now
        engagement.save(update_fields=["status", "activated_at"])
        return engagement


def suspend_engagement(*, engagement: ProviderEngagement) -> ProviderEngagement:
    """Suspend an active engagement."""
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(engagement.status, EngagementStatus.SUSPENDED)
        engagement.status = EngagementStatus.SUSPENDED
        engagement.suspended_at = now
        engagement.save(update_fields=["status", "suspended_at"])
        return engagement


def revoke_engagement(*, engagement: ProviderEngagement) -> ProviderEngagement:
    """Revoke an engagement (terminal state)."""
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(engagement.status, EngagementStatus.REVOKED)
        engagement.status = EngagementStatus.REVOKED
        engagement.revoked_at = now
        engagement.save(update_fields=["status", "revoked_at"])
        return engagement


def get_active_engagement(*, owner_tenant_id: str, provider_tenant_id: str) -> ProviderEngagement | None:
    """Return the active engagement for an owner-provider pair, or ``None``."""
    try:
        return ProviderEngagement.objects.get(
            owner_tenant_id=owner_tenant_id,
            provider_tenant_id=provider_tenant_id,
            status=EngagementStatus.ACTIVE,
        )
    except ProviderEngagement.DoesNotExist:
        return None


def assert_engagement_allows_sync(*, engagement: ProviderEngagement) -> None:
    """Raise ``EngagementSyncNotAllowed`` if the engagement cannot sync."""
    if engagement.status != EngagementStatus.ACTIVE:
        raise EngagementSyncNotAllowed(
            f"Engagement '{engagement}' is '{engagement.status}'; "
            f"only active engagements may synchronise data.",
        )
