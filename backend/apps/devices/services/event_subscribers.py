"""Pluggable subscribers for the device event bus.

These subscribers connect the in-process event bus to external systems:
- ``persist_to_store`` — durable event store (``DeviceDomainEvent``)
- ``publish_to_redis`` — Redis pub/sub for realtime fanout

Add them to the event bus at startup:

    from apps.devices.events import subscribe
    from apps.devices.services.event_subscribers import persist_to_store

    subscribe(persist_to_store)
"""

import json
import logging

logger = logging.getLogger("flower.devices.subscribers")


def persist_to_store(event) -> None:
    """Persist every device event to the durable event store.

    Register this as the first subscriber so the event store is
    always the canonical source of truth.
    """
    from apps.devices.models.domain_event import persist_event

    persist_event(event=event)


def publish_to_redis(event) -> None:
    """Publish device events to Redis pub/sub channels.

    Channel format: ``device:{tenant_schema}:{event_type}``

    This allows realtime consumers (WebSocket gateway, analytics pipeline)
    to subscribe to specific event types per tenant.
    """
    try:
        from django_redis import get_redis_connection
    except ImportError:
        logger.debug("django-redis not installed — skipping Redis pub/sub")
        return

    try:
        conn = get_redis_connection("default")
        channel = f"device:{event.tenant_schema}:{event.event_type}"
        payload = json.dumps(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "device_serial": event.device_serial,
                "device_uuid": event.device_uuid,
                "tenant_schema": event.tenant_schema,
                "timestamp": event.timestamp,
                "data": event.data,
                "correlation_id": event.correlation_id,
            },
            default=str,
        )
        conn.publish(channel, payload)

        # Also publish to wildcard channel for global listeners.
        conn.publish(f"device:*:{event.event_type}", payload)
    except Exception:
        logger.exception(
            "redis_publish_failed",
            extra={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "device_serial": event.device_serial,
            },
        )
