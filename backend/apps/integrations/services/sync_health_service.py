"""Sync health monitoring and metrics.

Provides engagement-level sync health summaries and a metrics abstraction
for Prometheus integration.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.db.models import Min
from django.utils import timezone

from apps.integrations.domain.enums import EngagementStatus, OutboxStatus, SyncRunStatus
from apps.integrations.domain.constants import SYNC_RUN_TIMEOUT_SECONDS
from apps.integrations.models import IntegrationOutbox, ProviderEngagement, SyncRun


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SyncHealthSummary:
    total_engagements: int = 0
    active_engagements: int = 0
    running_sync_count: int = 0
    failed_sync_count_24h: int = 0
    stuck_sync_count: int = 0
    total_dead_letter_count: int = 0
    total_retry_count: int = 0


@dataclass
class EngagementSyncHealth:
    engagement_id: int
    owner_tenant_id: str
    provider_tenant_id: str
    engagement_status: str
    last_successful_sync: Any = None  # datetime | None
    last_failed_sync: Any = None
    running_sync_count: int = 0
    failed_sync_count: int = 0
    checkpoint_age_seconds: float | None = None
    retry_queue_size: int = 0
    dead_letter_count: int = 0
    overall_healthy: bool = True


# ---------------------------------------------------------------------------
# Metrics counters (not Prometheus-dependent)
# ---------------------------------------------------------------------------

# These are in-memory counters for the current process lifetime.
# Replace with Prometheus counters when the infrastructure is ready.
_sync_metrics: dict[str, int | float] = {
    "runs_total": 0,
    "runs_failed_total": 0,
    "duration_seconds": 0,
    "stuck_total": 0,
    "delta_runs_total": 0,
    "full_runs_total": 0,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_sync_health_summary() -> SyncHealthSummary:
    """Return an aggregated sync health summary across all engagements."""
    now = timezone.now()
    stuck_threshold = now - timedelta(seconds=SYNC_RUN_TIMEOUT_SECONDS)

    total = ProviderEngagement.objects.count()
    active = ProviderEngagement.objects.filter(status=EngagementStatus.ACTIVE).count()

    running = SyncRun.objects.filter(
        status__in={SyncRunStatus.PENDING, SyncRunStatus.RUNNING},
    ).count()

    failed_24h = SyncRun.objects.filter(
        status=SyncRunStatus.FAILED,
        failed_at__gte=now - timedelta(hours=24),
    ).count()

    stuck = SyncRun.objects.filter(
        status=SyncRunStatus.RUNNING,
        started_at__lte=stuck_threshold,
    ).count()

    dead_letter = IntegrationOutbox.objects.filter(status=OutboxStatus.DEAD_LETTER).count()
    retry = IntegrationOutbox.objects.filter(status=OutboxStatus.RETRY).count()

    return SyncHealthSummary(
        total_engagements=total,
        active_engagements=active,
        running_sync_count=running,
        failed_sync_count_24h=failed_24h,
        stuck_sync_count=stuck,
        total_dead_letter_count=dead_letter,
        total_retry_count=retry,
    )


def get_engagement_sync_health(*, engagement: ProviderEngagement) -> EngagementSyncHealth:
    """Return detailed sync health for a single engagement."""
    from apps.integrations.models import SyncCheckpoint

    now = timezone.now()

    last_successful = (
        SyncRun.objects.filter(engagement=engagement, status=SyncRunStatus.COMPLETED)
        .order_by("-completed_at")
        .first()
    )
    last_failed = (
        SyncRun.objects.filter(engagement=engagement, status=SyncRunStatus.FAILED)
        .order_by("-failed_at")
        .first()
    )
    running_count = SyncRun.objects.filter(
        engagement=engagement,
        status__in={SyncRunStatus.PENDING, SyncRunStatus.RUNNING},
    ).count()
    failed_count = SyncRun.objects.filter(engagement=engagement, status=SyncRunStatus.FAILED).count()

    # Checkpoint age: find the oldest checkpoint for this engagement
    oldest_cp = SyncCheckpoint.objects.filter(engagement=engagement).aggregate(
        oldest=Min("last_event_created_at"),
    )
    checkpoint_age = None
    if oldest_cp.get("oldest"):
        checkpoint_age = (now - oldest_cp["oldest"]).total_seconds()

    # Retry / dead letter (approximate — counts events targeting this provider)
    retry_count = IntegrationOutbox.objects.filter(
        status=OutboxStatus.RETRY,
        target_provider_schema=engagement.provider_tenant_id,
    ).count()
    dead_letter_count = IntegrationOutbox.objects.filter(
        status=OutboxStatus.DEAD_LETTER,
        target_provider_schema=engagement.provider_tenant_id,
    ).count()

    unhealthy = bool(
        running_count > 0
        or failed_count > 3
        or (checkpoint_age is not None and checkpoint_age > 86400)
    )

    return EngagementSyncHealth(
        engagement_id=engagement.pk,
        owner_tenant_id=engagement.owner_tenant_id,
        provider_tenant_id=engagement.provider_tenant_id,
        engagement_status=engagement.status,
        last_successful_sync=last_successful.completed_at if last_successful else None,
        last_failed_sync=last_failed.failed_at if last_failed else None,
        running_sync_count=running_count,
        failed_sync_count=failed_count,
        checkpoint_age_seconds=checkpoint_age,
        retry_queue_size=retry_count,
        dead_letter_count=dead_letter_count,
        overall_healthy=not unhealthy,
    )


def detect_unhealthy_engagements() -> list[EngagementSyncHealth]:
    """Return sync health for all engagements that appear unhealthy."""
    unhealthy = []
    for engagement in ProviderEngagement.objects.filter(status=EngagementStatus.ACTIVE):
        health = get_engagement_sync_health(engagement=engagement)
        if not health.overall_healthy:
            unhealthy.append(health)
    return unhealthy


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def increment_metric(name: str, value: int | float = 1) -> None:
    """Increment a sync metric counter."""
    if name in _sync_metrics:
        _sync_metrics[name] += value
    else:
        _sync_metrics[name] = value


def set_metric(name: str, value: int | float) -> None:
    """Set a sync metric to an absolute value."""
    _sync_metrics[name] = value


def observe_duration(seconds: float) -> None:
    """Record a sync duration for the running average."""
    current = _sync_metrics.get("duration_seconds", 0)
    count = _sync_metrics.get("runs_total", 0)
    if count > 0:
        _sync_metrics["duration_seconds"] = ((current * (count - 1)) + seconds) / count
    else:
        _sync_metrics["duration_seconds"] = seconds


def get_metrics_snapshot() -> dict[str, int | float]:
    """Return a snapshot of all current sync metrics."""
    return dict(_sync_metrics)
