"""Durable, append-only domain event store for device lifecycle events.

Every ``DeviceEvent`` emitted through the event bus is persisted here as
an immutable ``DeviceDomainEvent`` row.  This provides:

- **Event replay** — rebuild projections from the event log.
- **Causal chain** — ``causation_id`` links events triggered by other events.
- **Durable fanout** — the event store is the canonical source; subscribers
  (Redis pub/sub, WebSocket, analytics) consume from it.
- **Outbox bridge** — events can be relayed to Kafka/NATS/Redpanda later.

Model follows domain-driven event sourcing patterns:
- ``aggregate_type`` = ``"Device"``
- ``aggregate_id`` = ``device.serial_number`` or ``device.uuid``
- ``event_type`` = canonical ``device.<past_tense>``
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class DeviceDomainEvent(models.Model):
    """Append-only device domain event.

    Rows are never modified or deleted.  The table is the canonical event
    log for the entire device subsystem.
    """

    event_id = models.CharField(
        max_length=64,
        unique=True,
        verbose_name=_("event ID"),
        help_text=_("UUID4 string — matches DeviceEvent.event_id."),
    )
    event_type = models.CharField(
        max_length=120,
        verbose_name=_("event type"),
        help_text=_("Canonical device.<past_tense> event type."),
    )
    aggregate_type = models.CharField(
        max_length=64,
        default="Device",
        verbose_name=_("aggregate type"),
    )
    aggregate_id = models.CharField(
        max_length=120,
        verbose_name=_("aggregate ID"),
        help_text=_("Device serial_number."),
    )
    payload = models.JSONField(
        default=dict, blank=True, verbose_name=_("payload"),
    )
    correlation_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("correlation ID"),
    )
    causation_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("causation ID"),
        help_text=_("event_id of the event that caused this one."),
    )
    tenant_schema = models.CharField(
        max_length=63,
        verbose_name=_("tenant schema"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        verbose_name = _("device domain event")
        verbose_name_plural = _("device domain events")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["aggregate_id", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
            models.Index(fields=["tenant_schema", "-created_at"]),
            models.Index(fields=["correlation_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.aggregate_id} @ {self.created_at})"


def persist_event(*, event) -> DeviceDomainEvent:
    """Persist a ``DeviceEvent`` to the durable event store.

    Called from the event bus when a subscriber needs durable storage.
    Uses ``get_or_create`` for idempotency — events with the same
    ``event_id`` are never duplicated.
    """
    row, _created = DeviceDomainEvent.objects.get_or_create(
        event_id=event.event_id,
        defaults={
            "event_type": event.event_type,
            "aggregate_type": "Device",
            "aggregate_id": event.device_serial,
            "payload": {
                "device_uuid": event.device_uuid,
                **event.data,
            },
            "correlation_id": event.correlation_id,
            "tenant_schema": event.tenant_schema,
        },
    )
    return row


def replay_events(
    *,
    aggregate_id: str,
    event_types: list[str] | None = None,
    limit: int = 1000,
) -> list[DeviceDomainEvent]:
    """Replay events for a specific device aggregate.

    Returns events in chronological order.  Optionally filter by event types.
    Useful for rebuilding projections.
    """
    qs = DeviceDomainEvent.objects.filter(aggregate_id=aggregate_id)
    if event_types:
        qs = qs.filter(event_type__in=event_types)
    return list(qs.order_by("created_at")[:limit])


def get_events_by_correlation(
    *,
    correlation_id: str,
    limit: int = 100,
) -> list[DeviceDomainEvent]:
    """Return all events with the same correlation_id (request trace)."""
    return list(
        DeviceDomainEvent.objects.filter(correlation_id=correlation_id).order_by(
            "created_at"
        )[:limit]
    )


def get_causal_chain(
    *,
    event_id: str,
    max_depth: int = 20,
) -> list[DeviceDomainEvent]:
    """Walk the causation chain from an event backwards.

    Returns events in causal order (root cause first, result event last).
    """
    chain = []
    seen = set()
    current_id = event_id

    for _ in range(max_depth):
        try:
            event = DeviceDomainEvent.objects.get(event_id=current_id)
        except DeviceDomainEvent.DoesNotExist:
            break
        if event.event_id in seen:
            break  # cycle detection
        seen.add(event.event_id)
        chain.append(event)
        if not event.causation_id:
            break
        current_id = event.causation_id

    chain.reverse()
    return chain
