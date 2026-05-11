from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.integrations.domain.enums import SyncItemStatus, SyncRunStatus, SyncRunType


class SyncRun(models.Model):
    """Tracks a single synchronisation run between owner and provider.

    A sync run is created when an active engagement starts a sync cycle.
    The run_type determines whether it is a full resync, a delta update,
    or a partial resync of a subset.

    Terminal statuses: ``completed``, ``failed``, ``cancelled``.
    """

    engagement = models.ForeignKey(
        "integrations.ProviderEngagement",
        on_delete=models.CASCADE,
        related_name="sync_runs",
        verbose_name=_("engagement"),
    )
    run_type = models.CharField(
        max_length=16,
        choices=SyncRunType.choices,
        verbose_name=_("run type"),
    )
    status = models.CharField(
        max_length=16,
        choices=SyncRunStatus.choices,
        default=SyncRunStatus.PENDING,
        verbose_name=_("status"),
    )
    started_at = models.DateTimeField(verbose_name=_("started at"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("completed at"),
    )
    failed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("failed at"),
    )
    error = models.TextField(
        null=True, blank=True, verbose_name=_("error"),
        help_text=_("Error detail when the run failed."),
    )
    stats = models.JSONField(
        default=dict, blank=True, verbose_name=_("stats"),
        help_text=_("Aggregated stats e.g. {'processed': 42, 'failed': 1}."),
    )

    class Meta:
        verbose_name = _("sync run")
        verbose_name_plural = _("sync runs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["engagement", "status"]),
            models.Index(fields=["engagement", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.engagement_id}:{self.run_type}:{self.status}"


class SyncCheckpoint(models.Model):
    """Last-known-event pointer for an engagement data stream.

    The checkpoint is the authoritative record of how far a sync has
    progressed for a given ``stream_name`` (e.g. ``locations``,
    ``devices``, ``telemetry``).  A new sync run resumes from the
    checkpoint rather than replaying the full history.
    """

    engagement = models.ForeignKey(
        "integrations.ProviderEngagement",
        on_delete=models.CASCADE,
        related_name="sync_checkpoints",
        verbose_name=_("engagement"),
    )
    stream_name = models.CharField(
        max_length=64, verbose_name=_("stream name"),
    )
    last_event_id = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name=_("last event ID"),
        help_text=_("Outbox event UUID of the last successfully synced event."),
    )
    last_event_created_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("last event created at"),
        help_text=_("Timestamp of the last successfully synced event."),
    )
    last_successful_run = models.ForeignKey(
        SyncRun,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("last successful run"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("sync checkpoint")
        verbose_name_plural = _("sync checkpoints")
        ordering = ["engagement", "stream_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["engagement", "stream_name"],
                name="unique_sync_checkpoint_per_stream",
            ),
        ]
        indexes = [
            models.Index(fields=["engagement", "stream_name"]),
        ]

    def __str__(self) -> str:
        return f"{self.engagement_id}:{self.stream_name}"


class SyncItem(models.Model):
    """Individual event within a sync run.

    Each ``SyncItem`` corresponds to one outbox event that the sync
    engine attempted to process.  The status records whether it was
    processed, failed, or skipped.
    """

    sync_run = models.ForeignKey(
        SyncRun,
        on_delete=models.CASCADE,
        related_name="sync_items",
        verbose_name=_("sync run"),
    )
    event_id = models.CharField(
        max_length=255, verbose_name=_("event ID"),
    )
    event_type = models.CharField(
        max_length=128, verbose_name=_("event type"),
    )
    aggregate_type = models.CharField(
        max_length=128, verbose_name=_("aggregate type"),
    )
    aggregate_id = models.CharField(
        max_length=255, verbose_name=_("aggregate ID"),
    )
    status = models.CharField(
        max_length=16,
        choices=SyncItemStatus.choices,
        default=SyncItemStatus.PENDING,
        verbose_name=_("status"),
    )
    error = models.TextField(
        null=True, blank=True, verbose_name=_("error"),
        help_text=_("Error detail when processing failed."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    processed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("processed at"),
    )

    class Meta:
        verbose_name = _("sync item")
        verbose_name_plural = _("sync items")
        ordering = ["sync_run", "created_at"]
        indexes = [
            models.Index(fields=["sync_run", "status"]),
            models.Index(fields=["event_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.sync_run_id}:{self.event_type}:{self.status}"
