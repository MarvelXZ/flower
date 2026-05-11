"""
Firmware bounded context.

Responsible for firmware versions and OTA update tracking.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class FirmwareVersion(UUIDModel):
    """
    A released firmware binary for a specific device type.
    """

    version = models.CharField(
        max_length=50,
        verbose_name=_("version"),
    )
    device_type = models.CharField(
        max_length=50,
        choices=[
            ("esp32", "ESP32"),
            ("esp8266", "ESP8266"),
        ],
        verbose_name=_("device type"),
    )
    binary = models.FileField(
        upload_to="firmware/%Y/%m/",
        verbose_name=_("firmware binary"),
    )
    changelog = models.TextField(
        blank=True,
        verbose_name=_("changelog"),
    )
    is_stable = models.BooleanField(
        default=False,
        verbose_name=_("stable"),
        help_text=_("Only stable versions are offered for automatic updates."),
    )

    class Meta:
        verbose_name = _("firmware version")
        verbose_name_plural = _("firmware versions")
        unique_together = [("version", "device_type")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.device_type} v{self.version}"


class FirmwareUpdate(UUIDModel):
    """
    Tracks the progress of an OTA firmware update for a device.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        DOWNLOADING = "downloading", _("Downloading")
        FLASHING = "flashing", _("Flashing")
        REBOOTING = "rebooting", _("Rebooting")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="firmware_updates",
        verbose_name=_("device"),
    )
    target_version = models.ForeignKey(
        FirmwareVersion,
        on_delete=models.PROTECT,
        verbose_name=_("target version"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("status"),
    )
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("progress percent"),
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
        verbose_name = _("firmware update")
        verbose_name_plural = _("firmware updates")
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.device.name} → {self.target_version.version} ({self.status})"
