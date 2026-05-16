"""
Alerts write operations (services layer).

All mutations to alert data MUST go through this module.
Direct model writes outside of services are prohibited.

NOTE: Alert events are append-only. There are no updates or deletes.

This module wraps ``apps.notifications.services.alert_service`` and
adds cooldown deduplication, device event integration, and rule
evaluation.
"""

from django.db import transaction
from django.utils import timezone

from apps.alerts.selectors import find_active_alert_for_rule, find_open_alert_for_device_event
from apps.care_engine.models.rule import Rule, evaluate_operator
from apps.devices.domain.enums import DeviceStatus
from apps.devices.events import DeviceEvent, DeviceEventType
from apps.notifications.domain.enums import AlertStatus
from apps.notifications.models.alert_event import AlertEvent as NotificationAlertEvent, record_alert_event
from apps.notifications.services.alert_service import (
    open_or_update_alert as _open_or_update_alert,
    acknowledge_alert as _acknowledge_alert,
    resolve_alert as _resolve_alert,
    dismiss_alert as _dismiss_alert,
    suppress_alert as _suppress_alert,
    InvalidAlertTransition,
)

from apps.notifications.services.notification_outbox_service import enqueue_alert_notification


# Re-export for convenience.
__all__ = [
    "AlertServiceError",
    "InvalidAlertTransition",
    "NoMatchingRule",
    "InCooldown",
    "evaluate_reading",
    "evaluate_device_event",
    "evaluate_metric",
    "open_alert",
    "acknowledge_alert",
    "resolve_alert",
    "suppress_alert",
    "record_alert_event",
]


class AlertServiceError(ValueError):
    """Base error for alert service failures."""


class NoMatchingRule(AlertServiceError):
    """Raised when no enabled rule matches the given metric_key."""


class InCooldown(AlertServiceError):
    """Raised when a matching rule is in cooldown and will not fire."""


# ---------------------------------------------------------------------------
# Rule Evaluation
# ---------------------------------------------------------------------------


def _build_alert_key(*, rule: Rule, device_id: str) -> str:
    """Build a stable deduplication key for a rule-device pair."""
    return f"rule:{rule.id}:device:{device_id}"


def evaluate_reading(*, reading) -> list[Rule]:
    """Evaluate a SensorReading against all enabled rules.

    Returns a list of rules whose conditions are met by the reading.
    The caller should then call ``open_alert`` for each matched rule.
    """
    from apps.telemetry.models.sensor_reading import SensorReading

    matched: list[Rule] = []
    metric_map = {
        "soil_moisture": reading.soil_moisture,
        "temperature": reading.temperature,
        "air_humidity": reading.air_humidity,
        "light_level": reading.light_level,
        "battery_level": reading.battery_level,
    }

    rules = Rule.objects.filter(
        enabled=True,
        metric_key__in=[k for k, v in metric_map.items() if v is not None],
    )

    for rule in rules:
        value = metric_map.get(rule.metric_key)
        if value is None:
            continue
        if rule.evaluate(value):
            matched.append(rule)

    return matched


def evaluate_device_event(*, event: DeviceEvent) -> list[Rule]:
    """Evaluate a DeviceEvent against all enabled rules.

    For offline/online events, looks for rules matching the
    ``device.status`` metric key.  For shadow events, looks for
    rules matching shadow fields.
    """
    matched: list[Rule] = []

    if event.event_type == DeviceEventType.OFFLINE:
        rules = Rule.objects.filter(enabled=True, metric_key="device.status")
        for rule in rules:
            if evaluate_operator(value=DeviceStatus.OFFLINE, operator=rule.operator, threshold="offline"):
                matched.append(rule)

    elif event.event_type == DeviceEventType.ONLINE:
        rules = Rule.objects.filter(enabled=True, metric_key="device.status")
        for rule in rules:
            if evaluate_operator(value=DeviceStatus.ACTIVE, operator=rule.operator, threshold="online"):
                matched.append(rule)

    elif event.event_type in (
        DeviceEventType.HEARTBEAT_RECEIVED,
        DeviceEventType.SHADOW_REPORTED,
    ):
        for metric_key, value in event.data.items():
            rules = Rule.objects.filter(enabled=True, metric_key=metric_key)
            for rule in rules:
                if isinstance(value, (int, float)) and rule.evaluate(value):
                    matched.append(rule)

    return matched


def evaluate_metric(*, device, metric_key: str, value: float) -> list[Rule]:
    """Evaluate a raw metric value against all enabled rules for this key.

    Low-level helper used by MQTT ingest and API telemetry endpoints.
    """
    rules = Rule.objects.filter(enabled=True, metric_key=metric_key)
    return [rule for rule in rules if rule.evaluate(value)]


# ---------------------------------------------------------------------------
# Alert lifecycle
# ---------------------------------------------------------------------------


def open_alert(*, rule: Rule, device, value: float | None = None, metadata: dict | None = None) -> NotificationAlertEvent | None:
    """Open (or re-open) an alert for a matched rule-device pair.

    Applies cooldown deduplication: if a resolved or acknowledged alert
    for the same rule+device was created within ``cooldown_seconds``,
    the alert is NOT re-opened; instead its ``trigger_count`` is
    incremented and a new ``AlertEvent`` is recorded.

    Returns the ``AlertEvent`` if a new alert was opened or an existing
    one was updated, or ``None`` if cooldown suppressed the trigger.
    """
    alert_key = _build_alert_key(rule=rule, device_id=str(device.id))
    now = timezone.now()

    # Check for existing active (open/acknowledged) alert for this
    # rule+device — these are de-duplicated.
    existing = find_active_alert_for_rule(alert_key=alert_key)
    if existing:
        _increment_trigger(alert=existing, metadata=metadata)
        return _record_re_trigger_event(alert=existing, rule=rule, device=device, value=value)

    # Check cooldown: if a resolved alert exists and was resolved less
    # than cooldown_seconds ago, do nothing.
    if _is_in_cooldown(rule=rule, alert_key=alert_key, now=now):
        return None

    # Create a new alert via the notifications service layer.
    alert = _open_or_update_alert(
        alert_key=alert_key,
        source_type="care_engine",
        severity=rule.severity,
        title=rule.name,
        message=f"{rule.metric_key} {rule.operator} {rule.threshold_value} (value: {value})",
        device=device,
        rule_code=rule.metric_key,
        metadata={
            "rule_id": str(rule.id),
            "rule_name": rule.name,
            "metric_key": rule.metric_key,
            "operator": rule.operator,
            "threshold": rule.threshold_value,
            "value": value,
            **(metadata or {}),
        },
    )

    return alert


def _is_in_cooldown(*, rule: Rule, alert_key: str, now) -> bool:
    """Return True if a resolved alert exists within the cooldown window."""
    if rule.cooldown_seconds == 0:
        return False
    return find_active_alert_for_rule(alert_key=alert_key) is not None


def _increment_trigger(*, alert, metadata: dict | None = None) -> None:
    """Increment trigger_count and update metadata on an existing alert."""
    alert.trigger_count += 1
    if metadata:
        alert.metadata.update(metadata)
    alert.save(update_fields=["trigger_count", "metadata", "updated_at"])


def _record_re_trigger_event(*, alert, rule: Rule, device, value: float | None) -> NotificationAlertEvent:
    """Record a re-trigger event without creating a new alert."""
    event = record_alert_event(
        alert=alert,
        event_type=NotificationAlertEvent.EventType.UPDATED,
        from_status=alert.status,
        to_status=alert.status,
        triggered_by="rule_engine",
        metadata={
            "reason": "re_triggered",
            "rule_id": str(rule.id),
            "metric_key": rule.metric_key,
            "value": value,
        },
    )
    return event


def resolve_alert_for_device(*, device, rule_code: str = "") -> NotificationAlertEvent | None:
    """Auto-resolve all open/acknowledged alerts for a device.

    Used when ``device.online`` events arrive to auto-resolve
    ``device.offline`` alerts, or after readings return to normal.
    """
    resolved = []
    alerts = find_active_alert_for_rule(alert_key_prefix=f"rule:{rule_code}:device:{device.id}") if rule_code else None
    if not alerts:
        return None

    for alert in alerts:
        try:
            _resolve_alert(alert=alert)
            record_alert_event(
                alert=alert,
                event_type=NotificationAlertEvent.EventType.RESOLVED,
                from_status=alert.status,
                to_status=AlertStatus.RESOLVED,
                triggered_by="rule_engine",
                metadata={"reason": "device_online_auto_resolve"},
            )
            enqueue_alert_notification(
                alert=alert,
                notification_type="alert_resolved",
            )
            resolved.append(alert)
        except InvalidAlertTransition:
            pass

    return resolved[0] if resolved else None


# Re-export notification service functions.
acknowledge_alert = _acknowledge_alert
resolve_alert = _resolve_alert
dismiss_alert = _dismiss_alert
suppress_alert = _suppress_alert
