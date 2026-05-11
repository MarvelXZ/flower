from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.provider_ops.domain.enums import (
    ProviderTaskEventType,
    ProviderTaskPriority,
    ProviderTaskStatus,
    ProviderTaskType,
)


class ProviderTask(models.Model):
    """Operational task for provider-side plant care and maintenance.

    Lives in the provider tenant schema.  References to owner data use
    external IDs (not FKs into the owner schema).
    """

    task_key = models.CharField(
        max_length=255, unique=True, verbose_name=_("task key"),
        help_text=_("Idempotency key — same task_key never creates a duplicate."),
    )
    source_owner_tenant_id = models.CharField(
        max_length=120, verbose_name=_("source owner tenant ID"),
    )
    external_alert_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("external alert ID"),
    )
    external_location_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("external location ID"),
    )
    external_plant_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("external plant ID"),
    )
    external_device_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("external device ID"),
    )
    task_type = models.CharField(
        max_length=32,
        choices=ProviderTaskType.choices,
        verbose_name=_("task type"),
    )
    priority = models.CharField(
        max_length=16,
        choices=ProviderTaskPriority.choices,
        default=ProviderTaskPriority.NORMAL,
        verbose_name=_("priority"),
    )
    status = models.CharField(
        max_length=16,
        choices=ProviderTaskStatus.choices,
        default=ProviderTaskStatus.OPEN,
        verbose_name=_("status"),
    )
    title = models.CharField(max_length=255, verbose_name=_("title"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    assignee_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("assignee ID"),
    )
    due_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("due at"),
    )
    started_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("started at"),
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("completed at"),
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("cancelled at"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("provider task")
        verbose_name_plural = _("provider tasks")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["task_type", "status"]),
            models.Index(fields=["assignee_id", "status"]),
            models.Index(fields=["due_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.task_key}:{self.status}"


class ProviderTaskEvent(models.Model):
    """Audit event for a provider task lifecycle transition."""

    task = models.ForeignKey(
        ProviderTask,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("task"),
    )
    event_type = models.CharField(
        max_length=32,
        choices=ProviderTaskEventType.choices,
        verbose_name=_("event type"),
    )
    actor_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("actor ID"),
    )
    message = models.TextField(blank=True, verbose_name=_("message"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("provider task event")
        verbose_name_plural = _("provider task events")
        ordering = ["task", "created_at"]

    def __str__(self) -> str:
        return f"{self.task_id}:{self.event_type}"


class ProviderTaskNote(models.Model):
    """Free-text note attached to a provider task."""

    task = models.ForeignKey(
        ProviderTask,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("task"),
    )
    actor_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("actor ID"),
    )
    body = models.TextField(verbose_name=_("body"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("provider task note")
        verbose_name_plural = _("provider task notes")
        ordering = ["task", "-created_at"]

    def __str__(self) -> str:
        return f"{self.task_id}:{self.body[:32]}"
