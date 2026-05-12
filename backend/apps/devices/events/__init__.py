"""Device domain events - canonical event backbone.

Every device state change emits a typed domain event.  These events feed:
- realtime notifications (WebSocket / Redis pub/sub)
- alerting engine (Rule & Alert Engine)
- analytics pipeline
- audit trail
- automation engine
- SLA monitoring

Event types follow the pattern: `device.<past_tense_verb>`.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


# ---------------------------------------------------------------------------
# Event type registry
# ---------------------------------------------------------------------------


class DeviceEventType:
    PROVISIONED = "device.provisioned"
    IDENTITY_CREATED = "device.identity_created"
    REGISTERED = "device.registered"
    ACTIVATED = "device.activated"
    DEACTIVATED = "device.deactivated"
    OFFLINE = "device.offline"
    ONLINE = "device.online"
    HEARTBEAT_RECEIVED = "device.heartbeat_received"
    SHADOW_REPORTED = "device.shadow_reported"
    SHADOW_DESIRED = "device.shadow_desired"
    FIRMWARE_ASSIGNED = "device.firmware_assigned"
    FIRMWARE_DOWNLOAD_STARTED = "device.firmware_download_started"
    FIRMWARE_FLASH_STARTED = "device.firmware_flash_started"
    FIRMWARE_COMPLETED = "device.firmware_completed"
    FIRMWARE_FAILED = "device.firmware_failed"
    CREDENTIAL_ROTATED = "device.credential_rotated"
    PROVISIONING_FAILED = "device.provisioning_failed"


# All valid event types.
ALL_DEVICE_EVENT_TYPES: set[str] = {
    v for k, v in vars(DeviceEventType).items()
    if not k.startswith("_") and isinstance(v, str)
}


# ---------------------------------------------------------------------------
# Event data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceEvent:
    """Canonical device domain event.

    Immutable by design - once emitted, never modified.
    """

    event_id: str
    event_type: str
    device_serial: str
    device_uuid: str
    tenant_schema: str
    timestamp: str
    data: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""

    def __post_init__(self):
        if self.event_type not in ALL_DEVICE_EVENT_TYPES:
            raise ValueError(f"Unknown device event type: {self.event_type}")

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        device_serial: str,
        device_uuid: str,
        tenant_schema: str,
        data: dict[str, Any] | None = None,
        correlation_id: str = "",
    ) -> "DeviceEvent":
        """Factory for creating a new device event with a generated event_id."""
        return cls(
            event_id=str(uuid4()),
            event_type=event_type,
            device_serial=device_serial,
            device_uuid=device_uuid,
            tenant_schema=tenant_schema,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data or {},
            correlation_id=correlation_id,
        )


# ---------------------------------------------------------------------------
# Event bus (in-process, pluggable)
# ---------------------------------------------------------------------------

# Global list of subscriber callables.  Each subscriber receives a
# `DeviceEvent` and may be synchronous or async.  In production, replace
# with Redis pub/sub or a message broker.
_subscribers: list = []


def subscribe(handler) -> None:
    """Register a handler to receive all device events."""
    _subscribers.append(handler)


def unsubscribe(handler) -> None:
    """Remove a previously registered handler."""
    if handler in _subscribers:
        _subscribers.remove(handler)


def emit(event: DeviceEvent) -> None:
    """Emit a device event to all registered subscribers.

    Subscribers are called synchronously in registration order.  If a
    subscriber raises, the exception is logged and subsequent subscribers
    still run.  Events are emitted within the same database transaction
    as the state change.
    """
    import logging

    logger = logging.getLogger("flower.devices.events")

    for handler in _subscribers:
        try:
            handler(event)
        except Exception:
            logger.exception(
                "device_event_handler_failed",
                extra={
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "device_serial": event.device_serial,
                },
            )


def clear_subscribers() -> None:
    """Remove all subscribers (useful in tests)."""
    _subscribers.clear()
