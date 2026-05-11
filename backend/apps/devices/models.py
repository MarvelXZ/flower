"""
Devices bounded context.

Responsible for ESP32 and other IoT device definitions,
firmware versions, and connectivity status.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class Device(UUIDModel):
    """
    IoT device registered within a tenant.

    Each device has a unique hardware identifier and is linked
    to a planter where it collects telemetry.
    """

    class Status(models.TextChoices):
        ONLINE = "online", _("Online")
        OFFLINE = "offline", _("Offline")
        PROVISIONING = "provisioning", _("Provisioning")

    name = models.CharField(
        max_length=100,
        verbose_name=_("device name"),
        help_text=_("Human-readable name for the device."),
    )
    device_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("hardware device ID"),
        help_text=_("Unique hardware identifier (e.g., MAC address, serial number)."),
    )
    device_type = models.CharField(
        max_length=50,
        choices=[
            ("esp32", "ESP32"),
            ("esp8266", "ESP8266"),
        ],
        default="esp32",
        verbose_name=_("device type"),
    )
    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("firmware version"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROVISIONING,
        verbose_name=_("status"),
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("last seen at"),
    )
    battery_level = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("battery level"),
        help_text=_("Battery level as a percentage (0-100)."),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("notes"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
        help_text=_("Inactive devices do not accept telemetry."),
    )

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "last_seen_at"]),
            models.Index(fields=["device_id"]),
            models.Index(fields=["is_active", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.device_id})"


class DeviceCredential(UUIDModel):
    """
    API credentials for a device.

    Each active device has exactly one credential pair.
    The api_secret is hashed before storage.
    """

    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name="credential",
        verbose_name=_("device"),
    )
    api_key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("API key"),
        help_text=_("Public API key sent in request headers."),
    )
    api_secret = models.CharField(
        max_length=255,
        verbose_name=_("API secret"),
        help_text=_("Hashed secret used to verify the API key."),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("last used at"),
    )

    class Meta:
        verbose_name = _("device credential")
        verbose_name_plural = _("device credentials")
        indexes = [
            models.Index(fields=["api_key", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"Credential for {self.device.name}"


class DeviceProvisioningToken(UUIDModel):
    """
    One-time token used during device factory provisioning.

    The device presents this token to exchange it for a
    permanent DeviceCredential.
    """

    device_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("device ID"),
    )
    token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name=_("provisioning token"),
    )
    expires_at = models.DateTimeField(
        verbose_name=_("expires at"),
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_("used"),
    )

    class Meta:
        verbose_name = _("provisioning token")
        verbose_name_plural = _("provisioning tokens")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Token for {self.device_id}"


class DeviceHeartbeat(UUIDModel):
    """
    Periodic health report from a device.

    Captures system-level metrics separate from sensor telemetry.
    Sent at regular intervals (e.g., every 60 seconds) to confirm
    device liveness and report system health.
    """

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="heartbeats",
        verbose_name=_("device"),
    )
    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("firmware version"),
    )
    uptime_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("uptime (seconds)"),
    )
    free_heap_kb = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("free heap (KB)"),
    )
    wifi_rssi = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Wi-Fi RSSI"),
        help_text=_("Signal strength in dBm (negative values)."),
    )
    reported_at = models.DateTimeField(
        verbose_name=_("reported at"),
        help_text=_("Timestamp from the device clock."),
    )
    message_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("message ID"),
        help_text=_("Idempotency key from the heartbeat payload."),
    )

    class Meta:
        verbose_name = _("device heartbeat")
        verbose_name_plural = _("device heartbeats")
        ordering = ["-reported_at"]
        indexes = [
            models.Index(fields=["device", "reported_at"]),
        ]

    def __str__(self) -> str:
        return f"Heartbeat {self.device.device_id} @ {self.reported_at}"
