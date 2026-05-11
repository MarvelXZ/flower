"""Alert lifecycle service.

All alert mutations go through this service layer — never write to
``Alert`` directly from views or tasks.
"""

from django.db import transaction
from django.utils import timezone

from apps.notifications.domain.enums import (
    AlertSeverity,
    AlertSourceType,
    AlertStatus,
    NotificationType,
)
from apps.notifications.models import Alert
from apps.notifications.services.notification_outbox_service import enqueue_alert_notification


class AlertServiceError(ValueError):
    """Base error for alert service failures."""


class InvalidAlertTransition(AlertServiceError):
    """Raised when an alert status transition is not allowed."""


# ---------------------------------------------------------------------------
# Allowed status transitions
# ---------------------------------------------------------------------------

_ALERT_TRANSITIONS: dict[str, set[str]] = {
    AlertStatus.OPEN: {AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED, AlertStatus.DISMISSED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.RESOLVED, AlertStatus.DISMISSED},
    AlertStatus.RESOLVED: set(),   # terminal
    AlertStatus.DISMISSED: set(),  # terminal
}


def _validate_transition(current: str, target: str) -> None:
    allowed = _ALERT_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidAlertTransition(
            f"Cannot transition alert from '{current}' to '{target}'.",
        )


def _active_alert_exists(*, alert_key: str) -> Alert | None:
    """Return an active (open/acknowledged) alert with the given key, or ``None``."""
    try:
        return Alert.objects.get(
            alert_key=alert_key,
            status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
        )
    except Alert.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def open_or_update_alert(
    *,
    alert_key: str,
    source_type: str = AlertSourceType.SENSOR_READING,
    source_id: str = "",
    severity: str = AlertSeverity.WARNING,
    title: str,
    message: str = "",
    plant=None,
    device=None,
    sensor_reading=None,
    rule_code: str = "",
    metadata: dict | None = None,
) -> Alert:
    """Create a new alert or update ``last_seen_at`` on an existing active one.

    Idempotent per ``alert_key``: if an open or acknowledged alert already
    exists with the same key, its ``last_seen_at`` and ``metadata`` are
    updated instead of creating a duplicate.
    """
    now = timezone.now()
    with transaction.atomic():
        existing = _active_alert_exists(alert_key=alert_key)
        if existing:
            existing.last_seen_at = now
            if metadata:
                existing.metadata.update(metadata)
            existing.save(update_fields=["last_seen_at", "metadata", "updated_at"])
            return existing

        alert = Alert.objects.create(
            alert_key=alert_key,
            source_type=source_type,
            source_id=source_id,
            severity=severity,
            status=AlertStatus.OPEN,
            title=title,
            message=message,
            plant=plant,
            device=device,
            sensor_reading=sensor_reading,
            rule_code=rule_code,
            first_seen_at=now,
            last_seen_at=now,
            metadata=metadata or {},
        )

        # Enqueue alert created notification — async delivery via worker.
        enqueue_alert_notification(
            alert=alert,
            notification_type=NotificationType.ALERT_CREATED,
        )

        return alert


def acknowledge_alert(*, alert: Alert) -> Alert:
    """Mark an open alert as acknowledged.

    Acknowledging does not resolve the underlying condition.
    """
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(alert.status, AlertStatus.ACKNOWLEDGED)
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = now
        alert.save(update_fields=["status", "acknowledged_at", "updated_at"])
        return alert


def resolve_alert(*, alert: Alert) -> Alert:
    """Mark an alert as resolved.

    Terminal status — the alert instance cannot transition further.
    A new occurrence of the same condition creates a new alert with a
    new ``alert_key`` scope.
    """
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(alert.status, AlertStatus.RESOLVED)
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = now
        alert.save(update_fields=["status", "resolved_at", "updated_at"])

        enqueue_alert_notification(
            alert=alert,
            notification_type=NotificationType.ALERT_RESOLVED,
        )

        return alert


def dismiss_alert(*, alert: Alert) -> Alert:
    """Dismiss an alert without resolving its root cause.

    Terminal status — the alert instance cannot transition further.
    """
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(alert.status, AlertStatus.DISMISSED)
        alert.status = AlertStatus.DISMISSED
        alert.dismissed_at = now
        alert.save(update_fields=["status", "dismissed_at", "updated_at"])
        return alert
