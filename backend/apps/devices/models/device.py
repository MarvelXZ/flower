import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.devices.domain.enums import DeviceStatus


class Device(models.Model):
    """IoT device registered in the owner tenant context."""

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("UUID"),
    )
    name = models.CharField(max_length=160, verbose_name=_("name"))
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
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    provisioned_at = models.DateTimeField(null=True, blank=True, verbose_name=_("provisioned at"))
    activated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("activated at"))
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("last seen at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["owner_tenant_schema", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.uuid})"


class DeviceCredential(models.Model):
    """Minimal API credential placeholder for device authentication wiring."""

    device = models.OneToOneField(
        Device,
        on_delete=models.CASCADE,
        related_name="credential",
        verbose_name=_("device"),
    )
    api_key = models.CharField(max_length=255, unique=True, verbose_name=_("API key"))
    api_secret = models.CharField(max_length=255, verbose_name=_("API secret"))
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name=_("last used at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("device credential")
        verbose_name_plural = _("device credentials")

    def __str__(self) -> str:
        return f"Credential for {self.device_id}"
