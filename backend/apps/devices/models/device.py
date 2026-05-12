import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.devices.domain.enums import DeviceStatus, ProvisioningStatus


class Device(models.Model):
    """IoT device registered in the owner tenant context.

    Each device belongs to exactly one owner tenant (``owner_tenant_schema``).
    Devices authenticate via MQTT (client certificate or JWT) and HTTP
    (HMAC-signed API requests using ``DeviceCredential``).

    Every device has a hardware identity (``serial_number``,
    ``hardware_revision``) and a current software identity
    (``firmware_version``).  The ``mqtt_client_id`` is the canonical
    MQTT client identifier and must match the topic ACL.
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("UUID"),
    )
    name = models.CharField(max_length=160, verbose_name=_("name"))
    serial_number = models.CharField(
        max_length=120,
        unique=True,
        verbose_name=_("serial number"),
        help_text=_("Factory-assigned hardware serial number."),
    )
    hardware_revision = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("hardware revision"),
    )
    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("firmware version"),
    )
    owner_tenant_schema = models.CharField(
        max_length=63,
        verbose_name=_("owner tenant schema"),
        help_text=_("Canonical owner schema for MQTT ingest routing."),
    )
    status = models.CharField(
        max_length=32,
        choices=DeviceStatus.choices,
        default=DeviceStatus.PROVISIONING,
        verbose_name=_("status"),
    )
    provisioning_status = models.CharField(
        max_length=32,
        choices=ProvisioningStatus.choices,
        default=ProvisioningStatus.UNPROVISIONED,
        verbose_name=_("provisioning status"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    mqtt_client_id = models.CharField(
        max_length=160,
        blank=True,
        default="",
        verbose_name=_("MQTT client ID"),
    )
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("last seen at"))
    last_ip = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("last IP address"),
    )
    heartbeat_interval_seconds = models.PositiveIntegerField(
        default=60,
        verbose_name=_("heartbeat interval (s)"),
    )
    capabilities = models.JSONField(
        default=list, blank=True, verbose_name=_("capabilities"),
        help_text=_("List of device capabilities (e.g. ['temperature', 'humidity', 'soil_moisture'])."),
    )
    provisioned_at = models.DateTimeField(null=True, blank=True, verbose_name=_("provisioned at"))
    activated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("activated at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["serial_number"]),
            models.Index(fields=["owner_tenant_schema", "status"]),
            models.Index(fields=["mqtt_client_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.serial_number or self.uuid})"


class DeviceCredential(models.Model):
    """Per-device API credential for HTTP-level HMAC authentication.

    ``api_key`` is transmitted in the ``X-Device-Key`` header.  ``api_secret``
    is the HMAC shared secret and is NEVER transmitted — the device signs
    each request with it.  Only ``api_secret_hash`` is stored in the database.

    For production, prefer a KMS or Vault-backed secret resolver.
    """

    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name="credential",
        verbose_name=_("device"),
    )
    api_key = models.CharField(max_length=255, unique=True, verbose_name=_("API key"))
    api_secret_hash = models.CharField(
        max_length=255,
        verbose_name=_("API secret hash"),
        help_text=_("Argon2 hash of the shared secret — never store the plaintext."),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name=_("last used at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    rotated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("rotated at"))

    class Meta:
        verbose_name = _("device credential")
        verbose_name_plural = _("device credentials")

    def __str__(self) -> str:
        return f"Credential for {self.device_id}"


class DeviceHeartbeat(models.Model):
    """Append-only heartbeat log for device connectivity tracking.

    Never overwritten — each heartbeat is a new row.  The most recent
    heartbeat is derived via ``SELECT ... ORDER BY received_at DESC LIMIT 1``.
    This preserves a full audit trail of device connectivity.
    """

    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="heartbeats",
        verbose_name=_("device"),
    )
    received_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("received at"),
    )
    firmware_version = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name=_("reported firmware version"),
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, verbose_name=_("IP address"),
    )
    rssi = models.IntegerField(
        null=True, blank=True, verbose_name=_("WiFi RSSI"),
    )
    battery_level = models.FloatField(
        null=True, blank=True, verbose_name=_("battery level"),
    )

    class Meta:
        verbose_name = _("device heartbeat")
        verbose_name_plural = _("device heartbeats")
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["device", "-received_at"]),
        ]

    def __str__(self) -> str:
        return f"Heartbeat {self.device_id} @ {self.received_at}"
