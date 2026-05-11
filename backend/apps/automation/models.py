"""
Automation bounded context.

Responsible for automation rules that trigger actions
based on telemetry thresholds, schedules, or alert events.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class AutomationRule(UUIDModel):
    """
    A rule that triggers an action when a condition is met.

    Examples:
    - When soil_moisture < 30%, create a "water plant" task
    - When battery < 10%, send notification to admin
    """

    class TriggerType(models.TextChoices):
        ALERT_CREATED = "alert_created", _("Alert Created")
        TELEMETRY_THRESHOLD = "telemetry_threshold", _("Telemetry Threshold")
        SCHEDULE = "schedule", _("Schedule")

    class ActionType(models.TextChoices):
        CREATE_TASK = "create_task", _("Create Task")
        SEND_NOTIFICATION = "send_notification", _("Send Notification")
        UPDATE_DEVICE = "update_device", _("Update Device")

    name = models.CharField(
        max_length=100,
        verbose_name=_("rule name"),
    )
    trigger_type = models.CharField(
        max_length=50,
        choices=TriggerType.choices,
        verbose_name=_("trigger type"),
    )
    trigger_config = models.JSONField(
        default=dict,
        verbose_name=_("trigger configuration"),
        help_text=_("JSON configuration for the trigger condition."),
    )
    action_type = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        verbose_name=_("action type"),
    )
    action_config = models.JSONField(
        default=dict,
        verbose_name=_("action configuration"),
        help_text=_("JSON configuration for the action to execute."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    class Meta:
        verbose_name = _("automation rule")
        verbose_name_plural = _("automation rules")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AutomationExecution(UUIDModel):
    """
    A single execution of an automation rule.

    Records whether the rule fired successfully or failed.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        RUNNING = "running", _("Running")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")

    rule = models.ForeignKey(
        AutomationRule,
        on_delete=models.CASCADE,
        related_name="executions",
        verbose_name=_("rule"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("status"),
    )
    triggered_by = models.CharField(
        max_length=100,
        verbose_name=_("triggered by"),
        help_text=_("Reference to the event that triggered this execution."),
    )
    result = models.JSONField(
        default=dict,
        verbose_name=_("result"),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("error message"),
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("started at"),
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("completed at"),
    )

    class Meta:
        verbose_name = _("automation execution")
        verbose_name_plural = _("automation executions")
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.rule.name} — {self.status}"
