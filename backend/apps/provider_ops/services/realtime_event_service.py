"""Realtime event publishing and replay service.

Hooks into task, SLA, and notification services to publish live events
and persist them for reconnect/resume.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.provider_ops.models import RealtimeEvent

logger = logging.getLogger(__name__)

_MAX_REPLAY_EVENTS = 500
_REPLAY_WINDOW_HOURS = 24


# ---------------------------------------------------------------------------
# Event publishing
# ---------------------------------------------------------------------------


def publish_event(
    *,
    tenant_schema: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
    version: int = 1,
) -> RealtimeEvent | None:
    """Persist a realtime event and attempt channel-layer broadcast.

    Always persists to DB for replay.  Broadcast is best-effort.
    Returns the event or ``None`` on failure.
    """
    try:
        event = RealtimeEvent.objects.create(
            tenant_schema=tenant_schema,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            version=version,
            payload=payload,
        )
        _broadcast_event(event)
        return event
    except Exception:
        logger.warning("realtime_publish_failed", extra={"event_type": event_type, "entity_id": str(entity_id)})
        return None


def _broadcast_event(event: RealtimeEvent) -> None:
    """Attempt to broadcast via Channels layer (best-effort)."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"tenant_{event.tenant_schema}",
                {
                    "type": "realtime.event",
                    "event_id": str(event.pk),
                    "event_type": event.event_type,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "version": event.version,
                    "timestamp": event.created_at.isoformat(),
                    "payload": event.payload,
                },
            )
    except Exception:
        logger.debug("realtime_broadcast_skipped")


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


def replay_events(*, tenant_schema: str, after_event_id: int | None = None, limit: int = 100) -> list[dict]:
    """Return persisted events for reconnect/resume.

    If ``after_event_id`` is provided, returns only events newer than that ID.
    Otherwise returns the most recent events within the replay window.
    """
    qs = RealtimeEvent.objects.filter(
        tenant_schema=tenant_schema,
        created_at__gte=timezone.now() - timedelta(hours=_REPLAY_WINDOW_HOURS),
    ).order_by("-created_at")

    if after_event_id:
        try:
            after_event = RealtimeEvent.objects.get(pk=after_event_id, tenant_schema=tenant_schema)
            qs = RealtimeEvent.objects.filter(
                tenant_schema=tenant_schema,
                created_at__gt=after_event.created_at,
            ).order_by("created_at")
        except RealtimeEvent.DoesNotExist:
            pass

    events = qs[:min(limit, _MAX_REPLAY_EVENTS)]
    out = []
    for e in events:
        out.append({
            "event_id": e.pk,
            "event_type": e.event_type,
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "version": e.version,
            "timestamp": e.created_at.isoformat(),
            "payload": e.payload,
        })
    return out


# ---------------------------------------------------------------------------
# Entity-specific publishers
# ---------------------------------------------------------------------------


def publish_task_event(*, task, event_type: str, tenant_schema: str) -> RealtimeEvent | None:
    return publish_event(
        tenant_schema=tenant_schema,
        event_type=event_type,
        entity_type="provider_task",
        entity_id=str(task.pk),
        version=getattr(task, "version", 1),
        payload={
            "task_id": task.pk,
            "title": getattr(task, "title", ""),
            "status": getattr(task, "status", ""),
            "priority": getattr(task, "priority", ""),
        },
    )


def publish_sla_event(*, task, tenant_schema: str) -> RealtimeEvent | None:
    sla = getattr(task, "sla", None)
    return publish_event(
        tenant_schema=tenant_schema,
        event_type="sla_breached" if getattr(sla, "breached_resolution_sla", False) else "sla_updated",
        entity_type="task_sla",
        entity_id=str(task.pk),
        version=getattr(sla, "version", 1) if sla else 1,
        payload={
            "task_id": task.pk,
            "breached_response": getattr(sla, "breached_response_sla", False),
            "breached_resolution": getattr(sla, "breached_resolution_sla", False),
            "escalation_level": getattr(sla, "escalation_level", 0),
        },
    )
