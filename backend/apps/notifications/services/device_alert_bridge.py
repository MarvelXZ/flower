"""Device event → Alert bridge subscriber.

Listens to ``device.offline`` and ``device.online`` events from the
device event bus and creates/resolves corresponding alerts.

Register at startup::

    from apps.devices.events import subscribe
    from apps.notifications.services.device_alert_bridge import on_device_event
    subscribe(on_device_event)
"""

import logging

from django.utils import timezone

from apps.devices.events import DeviceEventType
from apps.notifications.domain.enums import AlertSeverity, AlertSourceType, AlertStatus
from apps.notifications.models import Alert

logger = logging.getLogger("flower.alerts.device_bridge")


def on_device_event(event) -> None:
    """Handle device lifecycle events by creating or resolving alerts.

    This is a pluggable event bus subscriber.  It does not raise — errors
    are logged and the event bus continues to other subscribers.
    """
    if event.event_type == DeviceEventType.OFFLINE:
        _handle_device_offline(event)
    elif event.event_type == DeviceEventType.ONLINE:
        _handle_device_online(event)
    elif event.event_type == DeviceEventType.HEARTBEAT_RECEIVED:
        _maybe_resolve_offline_alert(event)
        _handle_battery_low(event)



def _handle_device_offline(event) -> None:
    """Create or update a device offline alert."""
    alert_key = f"device_offline:{event.device_serial}"
    now = timezone.now()

    existing = Alert.objects.filter(
        alert_key=alert_key,
        status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
    ).first()

    if existing:
        existing.last_seen_at = now
        existing.metadata["last_offline_at"] = event.timestamp
        existing.save(update_fields=["last_seen_at", "metadata", "updated_at"])
        logger.info(
            "device_offline_alert_updated",
            extra={"alert_key": alert_key, "device_serial": event.device_serial},
        )
        return

    Alert.objects.create(
        alert_key=alert_key,
        source_type=AlertSourceType.DEVICE,
        source_id=event.device_uuid,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        title=f"Device {event.device_serial} is offline",
        message=f"Device serial={event.device_serial} stopped sending heartbeats.",
        rule_code="device_offline",
        first_seen_at=now,
        last_seen_at=now,
        metadata={
            "device_serial": event.device_serial,
            "device_uuid": event.device_uuid,
            "last_offline_at": event.timestamp,
            "tenant_schema": event.tenant_schema,
        },
    )
    logger.info(
        "device_offline_alert_created",
        extra={"alert_key": alert_key, "device_serial": event.device_serial},
    )


def _handle_device_online(event) -> None:
    """Resolve an open device offline alert."""
    alert_key = f"device_offline:{event.device_serial}"
    now = timezone.now()

    alert = Alert.objects.filter(
        alert_key=alert_key,
        status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
    ).first()

    if not alert:
        return

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = now
    alert.message = f"Device {event.device_serial} is back online."
    alert.metadata["resolved_at"] = event.timestamp
    alert.save(update_fields=["status", "resolved_at", "message", "metadata", "updated_at"])
    logger.info(
        "device_offline_alert_resolved",
        extra={"alert_key": alert_key, "device_serial": event.device_serial},
    )


def _maybe_resolve_offline_alert(event) -> None:
    """If a device was offline but sends a heartbeat, resolve the alert."""
    alert_key = f"device_offline:{event.device_serial}"

    alert = Alert.objects.filter(
        alert_key=alert_key,
        status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
    ).first()

    if not alert:
        return

    # Device was offline — now it's sending heartbeats, resolve.
    now = timezone.now()
    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = now
    alert.metadata["resolved_by_heartbeat"] = True
    alert.metadata["resolved_at"] = event.timestamp
    alert.save(update_fields=["status", "resolved_at", "metadata", "updated_at"])
    logger.info(
        "device_offline_alert_resolved_by_heartbeat",
        extra={"alert_key": alert_key, "device_serial": event.device_serial},
    )


def _handle_battery_low(event) -> None:
    """Create a battery low alert from a heartbeat with low battery."""
    battery = event.data.get("battery_level")
    if battery is None or battery > 15.0:
        return

    alert_key = f"battery_low:{event.device_serial}"
    now = timezone.now()

    existing = Alert.objects.filter(
        alert_key=alert_key,
        status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
    ).first()

    if existing:
        existing.last_seen_at = now
        existing.metadata["battery_level"] = battery
        existing.save(update_fields=["last_seen_at", "metadata", "updated_at"])
        return

    Alert.objects.create(
        alert_key=alert_key,
        source_type=AlertSourceType.DEVICE,
        source_id=event.device_uuid,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.OPEN,
        title=f"Device {event.device_serial} battery low ({battery:.0f}%)",
        message=f"Battery level is {battery:.1f}% (threshold 15%).",
        rule_code="battery_low",
        first_seen_at=now,
        last_seen_at=now,
        metadata={
            "battery_level": battery,
            "device_serial": event.device_serial,
            "tenant_schema": event.tenant_schema,
        },
    )
