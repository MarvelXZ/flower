from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.domain.enums import AlertSeverity, AlertSourceType, AlertStatus


class Alert(models.Model):
    """Tenant alert created by care evaluation, telemetry, or integrations.

    Each alert is uniquely identified by ``alert_key`` while it is in an
    ``open`` or ``acknowledged`` status.  Once resolved or dismissed, the
    same ``alert_key`` can be reused for a new occurrence.
    """

    alert_key = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("alert key"),
        help_text=_("Deduplication key: unique while status is open/acknowledged."
                     " Blank default exists only for legacy migration safety;"
                     " runtime values are always set by the service layer."),
    )
    source_type = models.CharField(
        max_length=32,
        choices=AlertSourceType.choices,
        default=AlertSourceType.SENSOR_READING,
        verbose_name=_("source type"),
    )
    source_id = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("source ID"),
    )
    severity = models.CharField(
        max_length=32,
        choices=AlertSeverity.choices,
        default=AlertSeverity.INFO,
        verbose_name=_("severity"),
    )
    status = models.CharField(
        max_length=32,
        choices=AlertStatus.choices,
        default=AlertStatus.OPEN,
        verbose_name=_("status"),
    )
    title = models.CharField(max_length=180, verbose_name=_("title"))
    message = models.TextField(blank=True, verbose_name=_("message"))
    plant = models.ForeignKey(
        "plants.Plant",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alerts",
        verbose_name=_("plant"),
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alerts",
        verbose_name=_("device"),
    )
    sensor_reading = models.ForeignKey(
        "telemetry.SensorReading",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alerts",
        verbose_name=_("sensor reading"),
    )
    rule_code = models.CharField(
        max_length=64, blank=True, default="", verbose_name=_("rule code"),
        help_text=_("Identifier of the rule that triggered this alert."),
    )
    first_seen_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("first seen at"),
        help_text=_("Default is timezone.now for migration safety;"
                     " runtime values are always set by the service layer."),
    )
    last_seen_at = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("last seen at"),
        help_text=_("Default is timezone.now for migration safety;"
                     " runtime values are always set by the service layer."),
    )
    acknowledged_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("acknowledged at"),
    )
    resolved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("resolved at"),
    )
    dismissed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("dismissed at"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("alert")
        verbose_name_plural = _("alerts")
        ordering = ["-first_seen_at"]
        indexes = [
            models.Index(fields=["status", "severity"]),
            models.Index(fields=["alert_key", "status"]),
            models.Index(fields=["rule_code", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.rule_code}:{self.title}"
