"""Notification outbox lifecycle service.

All notification outbox mutations go through this service layer —
never write to ``NotificationOutbox`` directly from views or tasks.
"""

import uuid

from django.db import transaction
from django.utils import timezone

from apps.notifications.domain.enums import (
    NotificationStatus,
    RecipientType,
)
from apps.notifications.models import Alert, NotificationDelivery, NotificationOutbox
from apps.notifications.services.routing_service import check_preferences_allows, resolve_channels


class NotificationOutboxError(ValueError):
    """Base error for notification outbox service failures."""


class InvalidNotificationTransition(NotificationOutboxError):
    """Raised when a notification status transition is not allowed."""


# ---------------------------------------------------------------------------
# Allowed status transitions
# ---------------------------------------------------------------------------

_NOTIFICATION_TRANSITIONS: dict[str, set[str]] = {
    NotificationStatus.PENDING: {NotificationStatus.PROCESSING},
    NotificationStatus.RETRY: {NotificationStatus.PROCESSING},
    NotificationStatus.PROCESSING: {
        NotificationStatus.SENT,
        NotificationStatus.RETRY,
        NotificationStatus.FAILED,
        NotificationStatus.DEAD_LETTER,
    },
    NotificationStatus.SENT: set(),         # terminal
    NotificationStatus.FAILED: set(),        # terminal
    NotificationStatus.DEAD_LETTER: set(),   # terminal
}


def _validate_transition(current: str, target: str) -> None:
    allowed = _NOTIFICATION_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidNotificationTransition(
            f"Cannot transition notification from '{current}' to '{target}'.",
        )


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------


def _build_event_id(*, alert: Alert, notification_type: str) -> uuid.UUID:
    """Deterministic event ID for idempotency.

    Same alert + same notification type → same event_id → no duplicate.
    """
    raw = f"notification:{notification_type}:alert_{alert.pk}"
    return uuid.uuid5(uuid.NAMESPACE_DNS, raw)


def enqueue_alert_notification(
    *,
    alert: Alert,
    notification_type: str,
    channel: str | None = None,
    recipient_type: str = RecipientType.TENANT,
    recipient_id: str = "",
) -> list[NotificationOutbox]:
    """Create notification outbox records for an alert lifecycle event.

    Resolves the appropriate channels based on alert severity, checks
    recipient preferences, and enqueues one ``NotificationOutbox`` per
    allowed channel.  Returns all created records.

    Idempotent per (event_id, channel): calling this twice for the same
    ``(alert, notification_type, channel)`` returns the existing record.
    """
    now = timezone.now()
    severity = alert.severity or "info"

    if channel:
        channels = [channel]
    else:
        channels = resolve_channels(severity=severity)

    created: list[NotificationOutbox] = []

    for ch in channels:
        if not check_preferences_allows(
            recipient_type=recipient_type,
            recipient_id=recipient_id or "",
            channel=ch,
            severity=severity,
        ):
            continue

        event_id = _build_event_id(
            alert=alert,
            notification_type=f"{notification_type}:{ch}",
        )

        with transaction.atomic():
            existing = NotificationOutbox.objects.select_for_update().filter(
                event_id=event_id,
                status__in={
                    NotificationStatus.PENDING,
                    NotificationStatus.PROCESSING,
                    NotificationStatus.RETRY,
                },
            ).first()
            if existing:
                created.append(existing)
                continue

            notification = NotificationOutbox.objects.create(
                event_id=event_id,
                notification_type=notification_type,
                channel=ch,
                recipient_type=recipient_type,
                recipient_id=recipient_id or "",
                alert=alert,
                payload={
                    "alert_id": alert.pk,
                    "alert_key": alert.alert_key,
                    "title": alert.title,
                    "message": alert.message,
                    "severity": severity,
                    "rule_code": alert.rule_code,
                    "status": alert.status,
                },
                status=NotificationStatus.PENDING,
                available_at=now,
            )
            created.append(notification)

    return created


# ---------------------------------------------------------------------------
# Claim & process
# ---------------------------------------------------------------------------


def claim_pending_notifications(limit: int = 100) -> list[NotificationOutbox]:
    """Atomically claim pending/retry notifications for a worker batch."""
    now = timezone.now()
    with transaction.atomic():
        notifications = list(
            NotificationOutbox.objects.select_for_update(skip_locked=True).filter(
                status__in={NotificationStatus.PENDING, NotificationStatus.RETRY},
                available_at__lte=now,
            )[:limit]
        )
        for n in notifications:
            mark_processing(n)
    return notifications


def mark_processing(notification: NotificationOutbox) -> NotificationOutbox:
    """Transition pending/retry -> processing."""
    _validate_transition(notification.status, NotificationStatus.PROCESSING)
    notification.status = NotificationStatus.PROCESSING
    notification.save(update_fields=["status", "updated_at"])
    return notification


def mark_sent(
    notification: NotificationOutbox,
    provider_response: dict | None = None,
) -> NotificationOutbox:
    """Transition processing -> sent (terminal)."""
    now = timezone.now()
    _validate_transition(notification.status, NotificationStatus.SENT)
    notification.status = NotificationStatus.SENT
    notification.sent_at = now
    notification.attempt_count += 1
    notification.last_error = ""
    notification.save(update_fields=["status", "sent_at", "attempt_count", "last_error", "updated_at"])
    _record_delivery_attempt(notification, NotificationStatus.SENT, provider_response=provider_response)
    return notification


def mark_retry(
    notification: NotificationOutbox,
    error: str,
    retry_delay_seconds: int = 60,
) -> NotificationOutbox:
    """Transition processing -> retry."""
    _validate_transition(notification.status, NotificationStatus.RETRY)
    notification.status = NotificationStatus.RETRY
    notification.attempt_count += 1
    notification.last_error = error
    notification.available_at = timezone.now() + timezone.timedelta(seconds=retry_delay_seconds)
    notification.save(
        update_fields=["status", "attempt_count", "last_error", "available_at", "updated_at"],
    )
    _record_delivery_attempt(notification, NotificationStatus.RETRY, error=error)
    return notification


def mark_failed(notification: NotificationOutbox, error: str) -> NotificationOutbox:
    """Transition processing -> failed (terminal)."""
    now = timezone.now()
    _validate_transition(notification.status, NotificationStatus.FAILED)
    notification.status = NotificationStatus.FAILED
    notification.failed_at = now
    notification.attempt_count += 1
    notification.last_error = error
    notification.save(update_fields=["status", "failed_at", "attempt_count", "last_error", "updated_at"])
    _record_delivery_attempt(notification, NotificationStatus.FAILED, error=error)
    return notification


def mark_dead_letter(notification: NotificationOutbox, error: str) -> NotificationOutbox:
    """Transition processing -> dead_letter (terminal)."""
    _validate_transition(notification.status, NotificationStatus.DEAD_LETTER)
    notification.status = NotificationStatus.DEAD_LETTER
    notification.attempt_count += 1
    notification.last_error = error
    notification.save(update_fields=["status", "attempt_count", "last_error", "updated_at"])
    _record_delivery_attempt(notification, NotificationStatus.DEAD_LETTER, error=error)
    return notification


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _record_delivery_attempt(
    notification: NotificationOutbox,
    status: str,
    error: str = "",
    provider_response: dict | None = None,
) -> NotificationDelivery:
    return NotificationDelivery.objects.create(
        notification=notification,
        attempt_number=notification.attempt_count,
        status=status,
        channel=notification.channel,
        error=error,
        provider_response=provider_response or {},
    )
