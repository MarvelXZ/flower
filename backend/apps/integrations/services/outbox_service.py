from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.integrations.domain.constants import DEFAULT_RETRY_DELAY_SECONDS
from apps.integrations.domain.enums import OutboxStatus
from apps.integrations.models import OutboxDelivery
from apps.integrations.selectors.outbox_selectors import get_pending_outbox_events


class InvalidOutboxTransition(ValueError):
    """Raised when an outbox state transition is not allowed."""


def _require_status(event, allowed_statuses: set[str], target_status: str) -> None:
    if event.status not in allowed_statuses:
        allowed = ", ".join(sorted(allowed_statuses))
        raise InvalidOutboxTransition(
            f"Cannot transition outbox event from {event.status!r} to {target_status!r}; "
            f"allowed source statuses: {allowed}."
        )


def claim_pending_events(limit: int = 100):
    """Atomically claim pending/retry events for a worker batch."""
    with transaction.atomic():
        events = list(get_pending_outbox_events(limit=limit))
        for event in events:
            mark_processing(event)
    return events


def mark_processing(event):
    """Transition pending/retry -> processing."""
    _require_status(
        event,
        {OutboxStatus.PENDING, OutboxStatus.RETRY},
        OutboxStatus.PROCESSING,
    )
    event.status = OutboxStatus.PROCESSING
    event.save(update_fields=["status", "updated_at"])
    return event


def mark_processed(event):
    """Transition processing -> processed."""
    _require_status(event, {OutboxStatus.PROCESSING}, OutboxStatus.PROCESSED)
    event.status = OutboxStatus.PROCESSED
    event.processed_at = timezone.now()
    event.last_error = ""
    event.save(update_fields=["status", "processed_at", "last_error", "updated_at"])
    return event


def mark_retry(event, error: str, retry_delay_seconds: int = DEFAULT_RETRY_DELAY_SECONDS):
    """Transition processing -> retry."""
    _require_status(event, {OutboxStatus.PROCESSING}, OutboxStatus.RETRY)
    event.status = OutboxStatus.RETRY
    event.retry_count += 1
    event.last_error = error
    event.available_at = timezone.now() + timedelta(seconds=retry_delay_seconds)
    event.save(update_fields=["status", "retry_count", "last_error", "available_at", "updated_at"])
    return event


def mark_dead_letter(event, error: str):
    """Transition processing -> dead_letter."""
    _require_status(event, {OutboxStatus.PROCESSING}, OutboxStatus.DEAD_LETTER)
    event.status = OutboxStatus.DEAD_LETTER
    event.retry_count += 1
    event.last_error = error
    event.save(update_fields=["status", "retry_count", "last_error", "updated_at"])
    return event


def record_delivery_attempt(event, status, error=None, response_code=None):
    """Record one internal processing attempt for an outbox event."""
    attempt_number = getattr(event, "attempts", 0) + 1
    event.attempts = attempt_number
    event.save(update_fields=["attempts", "updated_at"])
    return OutboxDelivery.objects.create(
        outbox=event,
        attempt_number=attempt_number,
        status=status,
        error=error or "",
        error_message=error or "",
        response_code=response_code,
    )
