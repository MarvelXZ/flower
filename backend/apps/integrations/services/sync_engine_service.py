"""Owner-to-provider sync orchestration engine.

This module implements the three sync strategies:

* **Full sync** — replays every outbox event for a provider engagement from
  the beginning (no checkpoint).  Used for initial provider onboarding.
* **Delta sync** — resumes from the last checkpoint and processes only
  events that have been created since then.
* **Resync** — resets a single stream's checkpoint and replays it.

The engine delegates actual HTTP delivery to ``deliver_outbox_event``, so
HMAC signing, retry, and dead-letter logic are not duplicated here.
"""

import logging

from apps.integrations.domain.enums import (
    OutboxStatus,
    SyncItemStatus,
    SyncRunStatus,
    SyncRunType,
)
from apps.integrations.models import IntegrationOutbox, ProviderEngagement, SyncItem, SyncRun
from apps.integrations.services.outbox_delivery_service import deliver_outbox_event
from apps.integrations.services.sync_service import (
    SyncNotAllowed,
    cancel_sync_run,
    complete_sync_run,
    fail_sync_run,
    get_checkpoint,
    record_sync_item,
    start_sync_run,
    update_checkpoint,
)

logger = logging.getLogger(__name__)


class SyncEngineError(ValueError):
    """Base error for sync engine failures."""


class SyncEngineEventError(SyncEngineError):
    """Raised when a single event cannot be processed."""


# ---------------------------------------------------------------------------
# Stream names — map aggregate types to checkpoint stream names
# ---------------------------------------------------------------------------

_STREAM_MAP: dict[str, str] = {
    "Location": "locations",
    "Device": "devices",
    "SensorReading": "telemetry",
}

_REVERSE_STREAM_MAP: dict[str, str] = {
    "locations": "Location",
    "devices": "Device",
    "telemetry": "SensorReading",
}


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_full_sync(*, engagement: ProviderEngagement) -> SyncRun:
    """Execute a full synchronisation for all streams."""
    sync_run = start_sync_run(engagement=engagement, run_type=SyncRunType.FULL)
    _execute_sync_run(sync_run=sync_run, engagement=engagement)
    return sync_run


def run_delta_sync(*, engagement: ProviderEngagement) -> SyncRun:
    """Execute a delta synchronisation — resume from latest checkpoint."""
    sync_run = start_sync_run(engagement=engagement, run_type=SyncRunType.DELTA)
    _execute_sync_run(sync_run=sync_run, engagement=engagement)
    return sync_run


def run_resync(*, engagement: ProviderEngagement, stream_name: str) -> SyncRun:
    """Reset a single stream's checkpoint and re-sync it."""
    # Clear the checkpoint for this stream so the full history is replayed.
    from apps.integrations.models import SyncCheckpoint
    SyncCheckpoint.objects.filter(
        engagement=engagement,
        stream_name=stream_name,
    ).delete()

    sync_run = start_sync_run(engagement=engagement, run_type=SyncRunType.RESYNC)
    _execute_sync_run(sync_run=sync_run, engagement=engagement)
    return sync_run


# ---------------------------------------------------------------------------
# Core execution loop
# ---------------------------------------------------------------------------


def _execute_sync_run(*, sync_run: SyncRun, engagement: ProviderEngagement) -> None:
    """Execute a sync run from start to finish.

    Sets ``sync_run`` to ``running``, iterates through known streams, and
    finalises the run as ``completed`` or ``failed``.
    """
    try:
        _transition_to_running(sync_run)
        streams = _resolve_streams(sync_run.run_type, engagement)

        for stream_name, aggregate_type in streams:
            checkpoint = get_checkpoint(engagement=engagement, stream_name=stream_name)
            _process_stream(
                sync_run=sync_run,
                engagement=engagement,
                stream_name=stream_name,
                aggregate_type=aggregate_type,
                checkpoint=checkpoint,
            )

        total = sync_run.sync_items.count()
        failed = sync_run.sync_items.filter(status=SyncItemStatus.FAILED).count()
        processed = sync_run.sync_items.filter(status=SyncItemStatus.PROCESSED).count()
        complete_sync_run(
            sync_run=sync_run,
            stats={
                "total": total,
                "processed": processed,
                "failed": failed,
                "streams": len(streams),
            },
        )
    except SyncNotAllowed:
        cancel_sync_run(sync_run=sync_run, reason="Engagement no longer active.")
    except Exception as exc:
        logger.exception("sync_run_failed", extra={"sync_run_id": sync_run.pk})
        fail_sync_run(sync_run=sync_run, error=str(exc))


def _transition_to_running(sync_run: SyncRun) -> None:
    """Transition sync run from pending to running."""
    sync_run.status = SyncRunStatus.RUNNING
    sync_run.save(update_fields=["status"])


# ---------------------------------------------------------------------------
# Stream resolution
# ---------------------------------------------------------------------------


def _resolve_streams(run_type: str, engagement: ProviderEngagement) -> list[tuple[str, str]]:
    """Return ``(stream_name, aggregate_type)`` pairs to process.

    For ``full`` and ``resync``, all known streams are processed.  For
    ``delta``, only streams that have incoming pending outbox events newer
    than the checkpoint are processed.
    """
    all_pairs = [(stream, agg_type) for agg_type, stream in _STREAM_MAP.items()]

    if run_type in (SyncRunType.FULL, SyncRunType.RESYNC):
        return all_pairs

    # Delta: only process streams with events newer than checkpoint
    result = []
    for stream_name, aggregate_type in all_pairs:
        checkpoint = get_checkpoint(engagement=engagement, stream_name=stream_name)
        qs = IntegrationOutbox.objects.filter(
            aggregate_type=aggregate_type,
            status=OutboxStatus.PROCESSED,
        )
        if checkpoint and checkpoint.last_event_id:
            qs = qs.filter(created_at__gt=checkpoint.last_event_created_at)
        if qs.exists():
            result.append((stream_name, aggregate_type))

    return result


# ---------------------------------------------------------------------------
# Single stream processing
# ---------------------------------------------------------------------------


def _process_stream(
    *,
    sync_run: SyncRun,
    engagement: ProviderEngagement,
    stream_name: str,
    aggregate_type: str,
    checkpoint,
) -> None:
    """Process all events for one aggregate stream."""
    qs = IntegrationOutbox.objects.filter(
        aggregate_type=aggregate_type,
        status=OutboxStatus.PROCESSED,
    ).order_by("created_at")

    if checkpoint and checkpoint.last_event_id:
        qs = qs.filter(
            created_at__gt=checkpoint.last_event_created_at,
        )
    elif _is_full_sync(sync_run):
        pass  # No checkpoint — full sync, process everything
    else:
        return  # No checkpoint and not a full sync — nothing to do

    last_event = None
    for event in qs.iterator(chunk_size=100):
        try:
            _deliver_and_record(sync_run=sync_run, event=event, stream_name=stream_name)
            last_event = event
        except SyncEngineEventError:
            continue

    # Advance checkpoint with the last successfully processed event
    if last_event:
        update_checkpoint(
            engagement=engagement,
            stream_name=stream_name,
            event_id=str(last_event.event_id),
            event_created_at=last_event.created_at,
            sync_run=sync_run,
        )


def _is_full_sync(sync_run: SyncRun) -> bool:
    return sync_run.run_type in (SyncRunType.FULL, SyncRunType.RESYNC)


# ---------------------------------------------------------------------------
# Single event delivery
# ---------------------------------------------------------------------------


def _deliver_and_record(
    *,
    sync_run: SyncRun,
    event: IntegrationOutbox,
    stream_name: str,
) -> None:
    """Deliver one outbox event to the provider and record a SyncItem."""
    try:
        result = deliver_outbox_event(event)
    except Exception as exc:
        _record_failed_item(sync_run=sync_run, event=event, error=str(exc))
        raise SyncEngineEventError(str(exc)) from exc

    if result.status == OutboxStatus.PROCESSED:
        _record_processed_item(sync_run=sync_run, event=event)
    else:
        _record_failed_item(
            sync_run=sync_run,
            event=event,
            error=result.last_error or "Delivery failed",
        )
        raise SyncEngineEventError(result.last_error or "Delivery failed")


def _record_processed_item(*, sync_run: SyncRun, event: IntegrationOutbox) -> SyncItem:
    return record_sync_item(
        sync_run=sync_run,
        event_id=str(event.event_id),
        event_type=event.event_type,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        status=SyncItemStatus.PROCESSED,
    )


def _record_failed_item(
    *,
    sync_run: SyncRun,
    event: IntegrationOutbox,
    error: str,
) -> SyncItem:
    return record_sync_item(
        sync_run=sync_run,
        event_id=str(event.event_id),
        event_type=event.event_type,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        status=SyncItemStatus.FAILED,
        error=error,
    )
