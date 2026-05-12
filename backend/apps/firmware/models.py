"""
Firmware bounded context.

Responsible for firmware versions, OTA update tracking, and staged rollout.
"""

import hashlib

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class FirmwareVersion(UUIDModel):
    """A released firmware binary for a specific device type.

    Each version includes a ``checksum_sha256`` for integrity verification
    and a ``minimum_hardware_revision`` to prevent incompatible OTA updates.
    Staged rollout is controlled via ``rollout_stage``:
    - ``canary`` — deployed to 1-2 test devices.
    - ``staged`` — rolled out to a percentage of the fleet.
    - ``full`` — available to all compatible devices.
    """

    class RolloutStage(models.TextChoices):
        CANARY = "canary", _("Canary")
        STAGED = "staged", _("Staged")
        FULL = "full", _("Full")

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
    checksum_sha256 = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name=_("SHA-256 checksum"),
        help_text=_("Hex-encoded SHA-256 of the firmware binary for integrity verification."),
    )
    artifact_url = models.URLField(
        blank=True,
        default="",
        verbose_name=_("artifact URL"),
        help_text=_("External CDN URL for the firmware binary (optional)."),
    )
    minimum_hardware_revision = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("minimum hardware revision"),
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
    rollout_stage = models.CharField(
        max_length=20,
        choices=RolloutStage.choices,
        default=RolloutStage.CANARY,
        verbose_name=_("rollout stage"),
    )

    class Meta:
        verbose_name = _("firmware version")
        verbose_name_plural = _("firmware versions")
        unique_together = [("version", "device_type")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.device_type} v{self.version}"


class FirmwareDeployment(models.Model):
    """Per-device firmware deployment tracking.

    Each row represents one OTA deployment attempt for a specific device.
    The deployment lifecycle: ``pending → downloading → flashing → rebooting
    → completed | failed``.
    """

    class State(models.TextChoices):
        PENDING = "pending", _("Pending")
        DOWNLOADING = "downloading", _("Downloading")
        FLASHING = "flashing", _("Flashing")
        REBOOTING = "rebooting", _("Rebooting")
        COMPLETED = "completed", _("Completed")
        FAILED = "failed", _("Failed")

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="firmware_deployments",
        verbose_name=_("device"),
    )
    firmware = models.ForeignKey(
        FirmwareVersion,
        on_delete=models.PROTECT,
        verbose_name=_("firmware version"),
    )
    state = models.CharField(
        max_length=20,
        choices=State.choices,
        default=State.PENDING,
        verbose_name=_("state"),
    )
    progress_percent = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("progress percent"),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("error message"),
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("failure reason"),
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("started at"),
    )
    completed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("completed at"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("firmware deployment")
        verbose_name_plural = _("firmware deployments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "state"]),
        ]

    def __str__(self) -> str:
        return f"{self.device.name} → {self.firmware.version} ({self.state})"


# Keep legacy FirmwareUpdate for backward compatibility.
class FirmwareUpdate(UUIDModel):
    """Legacy OTA update tracker (kept for backward compatibility).

    New code should use ``FirmwareDeployment`` instead.
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
