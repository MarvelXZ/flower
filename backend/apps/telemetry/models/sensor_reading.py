from django.db import models
from django.utils.translation import gettext_lazy as _


class SensorReading(models.Model):
    """Time-series friendly sensor reading stored in the owner tenant schema."""

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="sensor_readings",
        verbose_name=_("device"),
    )
    measured_at = models.DateTimeField(db_index=True, verbose_name=_("measured at"))
    soil_moisture = models.FloatField(null=True, blank=True, verbose_name=_("soil moisture"))
    temperature = models.FloatField(null=True, blank=True, verbose_name=_("temperature"))
    air_humidity = models.FloatField(null=True, blank=True, verbose_name=_("air humidity"))
    light_level = models.FloatField(null=True, blank=True, verbose_name=_("light level"))
    battery_level = models.FloatField(null=True, blank=True, verbose_name=_("battery level"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("sensor reading")
        verbose_name_plural = _("sensor readings")
        ordering = ["-measured_at"]
        indexes = [
            models.Index(fields=["device", "measured_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.device_id} @ {self.measured_at}"
