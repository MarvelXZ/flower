"""
Telemetry bounded context.

Responsible for raw sensor readings and processed snapshots.

CRITICAL: Telemetry records are APPEND-ONLY. Never update or delete.
Devices MUST NOT write business state directly.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class SensorType(UUIDModel):
    """
    Registry of sensor types that devices can report.

    Examples: soil_moisture, temperature, light, battery.
    """

    key = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("sensor key"),
        help_text=_("Machine-readable identifier (e.g., soil_moisture)."),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("sensor name"),
        help_text=_("Human-readable name."),
    )
    unit = models.CharField(
        max_length=30,
        verbose_name=_("unit"),
        help_text=_("Unit of measurement (e.g., percent, celsius, lux)."),
    )
    min_value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("minimum value"),
    )
    max_value = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("maximum value"),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
    )

    class Meta:
        verbose_name = _("sensor type")
        verbose_name_plural = _("sensor types")
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.name} ({self.unit})"


class TelemetryRecord(UUIDModel):
    """
    A single raw sensor reading from a device.

    APPEND-ONLY. Records are never updated or deleted.
    If data is invalid, set is_valid=False and record the error.
    """

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="telemetry_records",
        verbose_name=_("device"),
    )
    sensor_type = models.ForeignKey(
        SensorType,
        on_delete=models.PROTECT,
        verbose_name=_("sensor type"),
    )
    value = models.FloatField(
        verbose_name=_("value"),
    )
    measured_at = models.DateTimeField(
        db_index=True,
        verbose_name=_("measured at"),
        help_text=_("Timestamp from the device clock."),
    )
    received_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("received at"),
        help_text=_("Timestamp when the server received the reading."),
    )
    message_id = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name=_("message ID"),
        help_text=_("Idempotency key from the device payload."),
    )
    raw_payload = models.JSONField(
        default=dict,
        verbose_name=_("raw payload"),
    )
    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("firmware version"),
    )
    is_valid = models.BooleanField(
        default=True,
        verbose_name=_("valid"),
        help_text=_("False if the reading failed validation."),
    )
    validation_error = models.TextField(
        blank=True,
        verbose_name=_("validation error"),
    )

    class Meta:
        verbose_name = _("telemetry record")
        verbose_name_plural = _("telemetry records")
        ordering = ["-measured_at"]
        unique_together = [("message_id",)]
        indexes = [
            models.Index(fields=["device", "sensor_type", "measured_at"]),
            models.Index(fields=["message_id"]),
            models.Index(fields=["device", "is_valid", "measured_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.device.device_id} / {self.sensor_type.key} = {self.value}"


class TelemetryBatch(UUIDModel):
    """
    Aggregated telemetry data for a device over a time period.

    Produced by background Celery tasks from raw TelemetryRecords.
    """

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="telemetry_batches",
        verbose_name=_("device"),
    )
    sensor_type = models.ForeignKey(
        SensorType,
        on_delete=models.PROTECT,
        verbose_name=_("sensor type"),
    )
    period_start = models.DateTimeField(
        verbose_name=_("period start"),
    )
    period_end = models.DateTimeField(
        verbose_name=_("period end"),
    )
    avg_value = models.FloatField(
        verbose_name=_("average value"),
    )
    min_value = models.FloatField(
        verbose_name=_("minimum value"),
    )
    max_value = models.FloatField(
        verbose_name=_("maximum value"),
    )
    record_count = models.PositiveIntegerField(
        verbose_name=_("record count"),
    )

    class Meta:
        verbose_name = _("telemetry batch")
        verbose_name_plural = _("telemetry batches")
        ordering = ["-period_start"]
        indexes = [
            models.Index(fields=["device", "sensor_type", "period_start"]),
        ]

    def __str__(self) -> str:
        return f"{self.device.device_id} / {self.sensor_type.key} ({self.period_start} - {self.period_end})"
