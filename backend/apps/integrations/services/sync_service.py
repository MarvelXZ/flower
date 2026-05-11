from django.db import transaction
from django.utils import timezone

from apps.integrations.domain.enums import SyncRunStatus, SyncRunType, SyncItemStatus
from apps.integrations.models import ProviderEngagement, SyncCheckpoint, SyncItem, SyncRun
from apps.integrations.services.engagement_service import (
    EngagementSyncNotAllowed,
    assert_engagement_allows_sync,
)


class SyncError(ValueError):
    """Base error for sync service failures."""


class SyncNotAllowed(SyncError):
    """Raised when sync is attempted on a disallowed engagement."""


class InvalidSyncRunTransition(SyncError):
    """Raised when a sync run status transition is invalid."""


class CheckpointNotUpdated(SyncError):
    """Raised when a checkpoint cannot be moved backwards."""


# ---------------------------------------------------------------------------
# Internal: status transition validation
# ---------------------------------------------------------------------------

_SYNC_RUN_TRANSITIONS: dict[str, set[str]] = {
    SyncRunStatus.PENDING: {SyncRunStatus.RUNNING, SyncRunStatus.CANCELLED},
    SyncRunStatus.RUNNING: {SyncRunStatus.COMPLETED, SyncRunStatus.FAILED, SyncRunStatus.CANCELLED},
    SyncRunStatus.COMPLETED: set(),      # terminal
    SyncRunStatus.FAILED: set(),         # terminal
    SyncRunStatus.CANCELLED: set(),      # terminal
}


def _validate_sync_run_transition(current_status: str, target_status: str) -> None:
    allowed = _SYNC_RUN_TRANSITIONS.get(current_status, set())
    if target_status not in allowed:
        raise InvalidSyncRunTransition(
            f"Cannot transition sync run from '{current_status}' to '{target_status}'.",
        )


# ---------------------------------------------------------------------------
# Sync run lifecycle
# ---------------------------------------------------------------------------


def start_sync_run(
    *,
    engagement: ProviderEngagement,
    run_type: str = SyncRunType.DELTA,
) -> SyncRun:
    """Create a new sync run for an active engagement.

    Raises ``SyncNotAllowed`` if the engagement is not ``active``.
    """
    try:
        assert_engagement_allows_sync(engagement=engagement)
    except EngagementSyncNotAllowed as exc:
        raise SyncNotAllowed(str(exc)) from exc

    with transaction.atomic():
        sync_run = SyncRun.objects.create(
            engagement=engagement,
            run_type=run_type,
            status=SyncRunStatus.PENDING,
            started_at=timezone.now(),
        )
        return sync_run


def complete_sync_run(
    *,
    sync_run: SyncRun,
    stats: dict | None = None,
) -> SyncRun:
    """Mark a running sync run as completed with optional stats."""
    now = timezone.now()
    with transaction.atomic():
        _validate_sync_run_transition(sync_run.status, SyncRunStatus.COMPLETED)
        sync_run.status = SyncRunStatus.COMPLETED
        sync_run.completed_at = now
        if stats:
            sync_run.stats = stats
        sync_run.save(update_fields=["status", "completed_at", "stats"])
        return sync_run


def fail_sync_run(
    *,
    sync_run: SyncRun,
    error: str,
) -> SyncRun:
    """Mark a running sync run as failed with an error message."""
    now = timezone.now()
    with transaction.atomic():
        _validate_sync_run_transition(sync_run.status, SyncRunStatus.FAILED)
        sync_run.status = SyncRunStatus.FAILED
        sync_run.failed_at = now
        sync_run.error = error
        sync_run.save(update_fields=["status", "failed_at", "error"])
        return sync_run


def cancel_sync_run(
    *,
    sync_run: SyncRun,
    reason: str = "",
) -> SyncRun:
    """Cancel a pending or running sync run."""
    now = timezone.now()
    with transaction.atomic():
        _validate_sync_run_transition(sync_run.status, SyncRunStatus.CANCELLED)
        sync_run.status = SyncRunStatus.CANCELLED
        sync_run.completed_at = now
        sync_run.error = reason
        sync_run.save(update_fields=["status", "completed_at", "error"])
        return sync_run


# ---------------------------------------------------------------------------
# Sync items
# ---------------------------------------------------------------------------


def record_sync_item(
    *,
    sync_run: SyncRun,
    event_id: str,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    status: str = SyncItemStatus.PENDING,
    error: str = "",
) -> SyncItem:
    """Record an individual sync item within a sync run."""
    with transaction.atomic():
        item = SyncItem.objects.create(
            sync_run=sync_run,
            event_id=event_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            status=status,
        )
        if error:
            SyncItem.objects.filter(pk=item.pk).update(error=error)
        return item


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


def update_checkpoint(
    *,
    engagement: ProviderEngagement,
    stream_name: str,
    event_id: str,
    event_created_at,
    sync_run: SyncRun | None = None,
) -> SyncCheckpoint:
    """Idempotently advance a sync checkpoint.

    The checkpoint is only updated if the new ``event_created_at`` is
    strictly newer than the existing checkpoint timestamp.  This prevents
    out-of-order delivery from rewinding progress.
    """
    with transaction.atomic():
        try:
            checkpoint = SyncCheckpoint.objects.select_for_update().get(
                engagement=engagement,
                stream_name=stream_name,
            )
            _advanced = _advance_checkpoint(checkpoint, event_id, event_created_at, sync_run)
            if not _advanced:
                return checkpoint
        except SyncCheckpoint.DoesNotExist:
            checkpoint = SyncCheckpoint.objects.create(
                engagement=engagement,
                stream_name=stream_name,
                last_event_id=event_id,
                last_event_created_at=event_created_at,
                last_successful_run=sync_run,
            )
        return checkpoint


def _advance_checkpoint(
    checkpoint: SyncCheckpoint,
    event_id: str,
    event_created_at,
    sync_run: SyncRun | None,
) -> bool:
    """Try to advance the checkpoint.  Returns ``True`` if updated."""
    current = checkpoint.last_event_created_at
    if current is not None and event_created_at <= current:
        return False
    checkpoint.last_event_id = event_id
    checkpoint.last_event_created_at = event_created_at
    checkpoint.last_successful_run = sync_run
    checkpoint.save(update_fields=["last_event_id", "last_event_created_at", "last_successful_run", "updated_at"])
    return True


def get_checkpoint(
    *,
    engagement: ProviderEngagement,
    stream_name: str,
) -> SyncCheckpoint | None:
    """Return the checkpoint for an engagement stream, or ``None``."""
    try:
        return SyncCheckpoint.objects.get(
            engagement=engagement,
            stream_name=stream_name,
        )
    except SyncCheckpoint.DoesNotExist:
        return None
