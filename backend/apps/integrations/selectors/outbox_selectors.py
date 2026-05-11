from django.utils import timezone

from apps.integrations.domain.enums import OutboxStatus
from apps.integrations.models import IntegrationOutbox

CLAIMABLE_STATUSES = (OutboxStatus.PENDING, OutboxStatus.RETRY)


def is_claimable_outbox_event(event, *, now=None) -> bool:
    """Return whether an event is currently eligible for worker claiming."""
    current_time = now or timezone.now()
    return event.status in CLAIMABLE_STATUSES and event.available_at <= current_time


def get_pending_outbox_events(limit: int = 100):
    """Return claimable outbox events ordered for fair worker processing.

    The returned queryset uses row-level locking with skip_locked. It must be
    evaluated inside a transaction by the claiming service.
    """
    now = timezone.now()
    return (
        IntegrationOutbox.objects.select_for_update(skip_locked=True)
        .filter(status__in=CLAIMABLE_STATUSES, available_at__lte=now)
        .order_by("available_at", "created_at")[:limit]
    )
