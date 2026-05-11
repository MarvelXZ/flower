from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.provider_ops.domain.enums import TaskEscalationType


class TaskSLA(models.Model):
    """SLA tracking for a provider task.

    Lives in the provider tenant schema alongside ``ProviderTask``.
    """

    task = models.OneToOneField(
        "provider_ops.ProviderTask",
        on_delete=models.CASCADE,
        related_name="sla",
        verbose_name=_("task"),
    )
    response_due_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("response due at"),
    )
    resolution_due_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("resolution due at"),
    )
    first_assigned_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("first assigned at"),
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("resolved at"),
    )
    breached_response_sla = models.BooleanField(
        default=False, verbose_name=_("breached response SLA"),
    )
    breached_resolution_sla = models.BooleanField(
        default=False, verbose_name=_("breached resolution SLA"),
    )
    escalation_level = models.PositiveIntegerField(
        default=0, verbose_name=_("escalation level"),
    )
    last_escalated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("last escalated at"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("task SLA")
        verbose_name_plural = _("task SLAs")
        indexes = [
            models.Index(fields=["breached_response_sla", "breached_resolution_sla"]),
            models.Index(fields=["escalation_level"]),
        ]

    def __str__(self) -> str:
        return f"SLA(task={self.task_id}): level={self.escalation_level}"


class TaskEscalationEvent(models.Model):
    """Audit trail for SLA breaches and escalations."""

    task = models.ForeignKey(
        "provider_ops.ProviderTask",
        on_delete=models.CASCADE,
        related_name="escalation_events",
        verbose_name=_("task"),
    )
    escalation_type = models.CharField(
        max_length=32,
        choices=TaskEscalationType.choices,
        verbose_name=_("escalation type"),
    )
    previous_priority = models.CharField(
        max_length=16, null=True, blank=True, verbose_name=_("previous priority"),
    )
    new_priority = models.CharField(
        max_length=16, null=True, blank=True, verbose_name=_("new priority"),
    )
    previous_assignee = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("previous assignee"),
    )
    new_assignee = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("new assignee"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("task escalation event")
        verbose_name_plural = _("task escalation events")
        ordering = ["task", "-created_at"]

    def __str__(self) -> str:
        return f"{self.task_id}:{self.escalation_type}"
