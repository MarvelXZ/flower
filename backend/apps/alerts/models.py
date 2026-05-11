"""
Alerts bounded context.

Responsible for alert definitions, alert instances, and thresholds.

CRITICAL: Alert events are append-only. Never update or delete.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditableModel, UUIDModel


class AlertRule(AuditableModel):
    """
    A rule defining when an alert should be triggered.

    Monitors a specific sensor type against a threshold condition.
    For example: "soil_moisture < 30% for 15 minutes".
    """

    class Condition(models.TextChoices):
        LT = "lt", _("Less Than")
        GT = "gt", _("Greater Than")
        LTE = "lte", _("Less Than or Equal")
        GTE = "gte", _("Greater Than or Equal")
        EQ = "eq", _("Equal")

    name = models.CharField(
        max_length=100,
        verbose_name=_("rule name"),
    )
    sensor_type = models.ForeignKey(
        "telemetry.SensorType",
        on_delete=models.CASCADE,
        related_name="alert_rules",
        verbose_name=_("sensor type"),
    )
    condition = models.CharField(
        max_length=5,
        choices=Condition.choices,
        verbose_name=_("condition"),
        help_text=_("Comparison operator for the threshold."),
    )
    threshold = models.FloatField(
        verbose_name=_("threshold"),
        help_text=_("Value to compare against."),
    )
    duration_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_("duration (minutes)"),
        help_text=_("How long the condition must persist before triggering. 0 = immediate."),
    )
    severity = models.CharField(
        max_length=20,
        choices=[
            ("info", _("Info")),
            ("warning", _("Warning")),
            ("critical", _("Critical")),
        ],
        default="warning",
        verbose_name=_("severity"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    class Meta:
        verbose_name = _("alert rule")
        verbose_name_plural = _("alert rules")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sensor_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.sensor_type.key} {self.condition} {self.threshold})"


class Alert(UUIDModel):
    """
    An active or resolved alert instance.

    Created when an AlertRule's condition is met.
    Can be acknowledged and resolved by users.
    """

    class Severity(models.TextChoices):
        INFO = "info", _("Info")
        WARNING = "warning", _("Warning")
        CRITICAL = "critical", _("Critical")

    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alerts",
        verbose_name=_("rule"),
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="alerts",
        verbose_name=_("device"),
    )
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.WARNING,
        verbose_name=_("severity"),
    )
    message = models.TextField(
        verbose_name=_("message"),
    )
    value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("triggering value"),
    )
    threshold = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("threshold value"),
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledged_alerts",
        verbose_name=_("acknowledged by"),
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("acknowledged at"),
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("resolved at"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
        help_text=_("False once the alert is resolved."),
    )

    class Meta:
        verbose_name = _("alert")
        verbose_name_plural = _("alerts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "is_active"]),
            models.Index(fields=["severity", "is_active"]),
            models.Index(fields=["is_active", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.severity}] {self.message}"


class AlertEvent(UUIDModel):
    """
    Append-only log of alert state transitions.

    Records every state change: triggered, acknowledged, resolved, auto_resolved.
    Never update or delete events.
    """

    class EventType(models.TextChoices):
        TRIGGERED = "triggered", _("Triggered")
        ACKNOWLEDGED = "acknowledged", _("Acknowledged")
        RESOLVED = "resolved", _("Resolved")
        AUTO_RESOLVED = "auto_resolved", _("Auto-Resolved")

    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("alert"),
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        verbose_name=_("event type"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alert_events",
        verbose_name=_("actor"),
        help_text=_("User who performed the action, if applicable."),
    )
    details = models.JSONField(
        default=dict,
        verbose_name=_("details"),
    )
    occurred_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("occurred at"),
    )

    class Meta:
        verbose_name = _("alert event")
        verbose_name_plural = _("alert events")
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["alert", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.alert} — {self.event_type}"
