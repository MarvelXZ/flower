"""Celery tasks for sync orchestration and scheduling."""

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.integrations.domain.constants import SYNC_RUN_TIMEOUT_SECONDS
from apps.integrations.domain.enums import EngagementStatus, SyncRunStatus
from apps.integrations.models import ProviderEngagement, SyncRun
from apps.integrations.services.sync_audit import (
    audit_sync_completed,
    audit_sync_failed,
    audit_sync_recovered,
    audit_sync_started,
)
from apps.integrations.services.sync_engine_service import run_delta_sync, run_full_sync, run_resync
from apps.integrations.services.sync_health_service import increment_metric, observe_duration
from apps.integrations.services.sync_locking import (
    SyncLockError,
    acquire_sync_lock,
    has_running_sync,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-engagement sync tasks
# ---------------------------------------------------------------------------


@shared_task(name="integrations.run_delta_sync_task", autoretry_for=(SyncLockError,), max_retries=2)
def run_delta_sync_task(engagement_id: int) -> dict:
    """Run a delta sync for a single engagement."""
    engagement = ProviderEngagement.objects.get(pk=engagement_id)
    acquire_sync_lock(engagement=engagement)
    sync_run = run_delta_sync(engagement=engagement)
    audit_sync_started(engagement_id=engagement.pk, run_id=sync_run.pk, run_type=sync_run.run_type)
    if sync_run.status == SyncRunStatus.COMPLETED:
        audit_sync_completed(engagement_id=engagement.pk, run_id=sync_run.pk, stats=sync_run.stats)
        increment_metric("delta_runs_total")
    elif sync_run.status == SyncRunStatus.FAILED:
        audit_sync_failed(engagement_id=engagement.pk, run_id=sync_run.pk, error=sync_run.error or "")
    increment_metric("runs_total")
    return {"engagement_id": engagement_id, "sync_run_id": sync_run.pk, "status": sync_run.status}


@shared_task(name="integrations.run_full_sync_task", autoretry_for=(SyncLockError,), max_retries=2)
def run_full_sync_task(engagement_id: int) -> dict:
    """Run a full sync for a single engagement."""
    engagement = ProviderEngagement.objects.get(pk=engagement_id)
    acquire_sync_lock(engagement=engagement)
    start = timezone.now()
    sync_run = run_full_sync(engagement=engagement)
    audit_sync_started(engagement_id=engagement.pk, run_id=sync_run.pk, run_type=sync_run.run_type)
    if sync_run.status == SyncRunStatus.COMPLETED:
        audit_sync_completed(engagement_id=engagement.pk, run_id=sync_run.pk, stats=sync_run.stats)
        observe_duration((timezone.now() - start).total_seconds())
        increment_metric("full_runs_total")
    elif sync_run.status == SyncRunStatus.FAILED:
        audit_sync_failed(engagement_id=engagement.pk, run_id=sync_run.pk, error=sync_run.error or "")
    increment_metric("runs_total")
    return {"engagement_id": engagement_id, "sync_run_id": sync_run.pk, "status": sync_run.status}


@shared_task(name="integrations.run_resync_task", autoretry_for=(SyncLockError,), max_retries=2)
def run_resync_task(engagement_id: int, stream_name: str) -> dict:
    """Run a resync for a single stream on an engagement."""
    engagement = ProviderEngagement.objects.get(pk=engagement_id)
    acquire_sync_lock(engagement=engagement)
    sync_run = run_resync(engagement=engagement, stream_name=stream_name)
    audit_sync_started(engagement_id=engagement.pk, run_id=sync_run.pk, run_type=sync_run.run_type)
    if sync_run.status == SyncRunStatus.COMPLETED:
        audit_sync_completed(engagement_id=engagement.pk, run_id=sync_run.pk, stats=sync_run.stats)
    elif sync_run.status == SyncRunStatus.FAILED:
        audit_sync_failed(engagement_id=engagement.pk, run_id=sync_run.pk, error=sync_run.error or "")
    increment_metric("runs_total")
    return {"engagement_id": engagement_id, "sync_run_id": sync_run.pk, "status": sync_run.status}


# ---------------------------------------------------------------------------
# Periodic / batch tasks
# ---------------------------------------------------------------------------


@shared_task(name="integrations.run_periodic_delta_syncs")
def run_periodic_delta_syncs() -> dict:
    """Run delta sync for all active engagements that are not already syncing."""
    results = {"attempted": 0, "skipped_running": 0, "errors": 0}
    for engagement in ProviderEngagement.objects.filter(status=EngagementStatus.ACTIVE):
        if has_running_sync(engagement=engagement):
            results["skipped_running"] += 1
            continue
        try:
            run_delta_sync_task.delay(engagement_id=engagement.pk)
            results["attempted"] += 1
        except Exception:
            logger.exception("periodic_delta_sync_error", extra={"engagement_id": engagement.pk})
            results["errors"] += 1
    return results


@shared_task(name="integrations.recover_stuck_sync_runs")
def recover_stuck_sync_runs() -> int:
    """Mark stuck running sync runs as failed."""
    from django.utils import timezone as tz
    threshold = tz.now() - tz.timedelta(seconds=SYNC_RUN_TIMEOUT_SECONDS)
    stuck = SyncRun.objects.filter(
        status=SyncRunStatus.RUNNING,
        started_at__lte=threshold,
    )
    count = 0
    for sync_run in stuck:
        try:
            with transaction.atomic():
                sync_run.status = SyncRunStatus.FAILED
                sync_run.failed_at = tz.now()
                sync_run.error = "sync_run_timeout"
                sync_run.save(update_fields=["status", "failed_at", "error"])
            audit_sync_recovered(run_id=sync_run.pk, error="sync_run_timeout")
            increment_metric("stuck_total")
            count += 1
        except Exception:
            logger.exception("stuck_recovery_error", extra={"sync_run_id": sync_run.pk})
    return count
