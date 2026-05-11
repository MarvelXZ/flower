from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class ExternalLocation(models.Model):
    """Provider-side copy of an owner location received over B2B API."""

    source_owner_tenant_id = models.CharField(
        max_length=120,
        verbose_name=_("source owner tenant ID"),
    )
    external_id = models.CharField(max_length=120, verbose_name=_("external ID"))
    name = models.CharField(max_length=180, verbose_name=_("name"))
    address = models.CharField(max_length=255, blank=True, verbose_name=_("address"))
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("latitude"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("longitude"),
    )
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name=_("raw payload"))
    last_synced_at = models.DateTimeField(default=timezone.now, verbose_name=_("last synced at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("external location")
        verbose_name_plural = _("external locations")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_owner_tenant_id", "external_id"],
                name="provider_external_location_source_external_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["source_owner_tenant_id", "external_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_owner_tenant_id}:{self.external_id}"


class ExternalDevice(models.Model):
    """Provider-side copy of an owner device received over B2B API."""

    source_owner_tenant_id = models.CharField(
        max_length=120,
        verbose_name=_("source owner tenant ID"),
    )
    external_id = models.CharField(max_length=120, verbose_name=_("external ID"))
    external_location = models.ForeignKey(
        ExternalLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="external_devices",
        verbose_name=_("external location"),
    )
    name = models.CharField(max_length=180, verbose_name=_("name"))
    status = models.CharField(max_length=64, verbose_name=_("status"))
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name=_("raw payload"))
    last_synced_at = models.DateTimeField(default=timezone.now, verbose_name=_("last synced at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("external device")
        verbose_name_plural = _("external devices")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_owner_tenant_id", "external_id"],
                name="provider_external_device_source_external_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["source_owner_tenant_id", "external_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_owner_tenant_id}:{self.external_id}"


class TelemetryIngest(models.Model):
    """Provider-side telemetry copy received from an owner B2B sync."""

    source_owner_tenant_id = models.CharField(
        max_length=120,
        verbose_name=_("source owner tenant ID"),
    )
    external_device = models.ForeignKey(
        ExternalDevice,
        on_delete=models.CASCADE,
        related_name="telemetry_ingests",
        verbose_name=_("external device"),
    )
    external_reading_id = models.CharField(max_length=120, verbose_name=_("external reading ID"))
    measured_at = models.DateTimeField(verbose_name=_("measured at"))
    soil_moisture = models.FloatField(null=True, blank=True, verbose_name=_("soil moisture"))
    temperature = models.FloatField(null=True, blank=True, verbose_name=_("temperature"))
    air_humidity = models.FloatField(null=True, blank=True, verbose_name=_("air humidity"))
    light_level = models.FloatField(null=True, blank=True, verbose_name=_("light level"))
    battery_level = models.FloatField(null=True, blank=True, verbose_name=_("battery level"))
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name=_("raw payload"))
    received_at = models.DateTimeField(auto_now_add=True, verbose_name=_("received at"))

    class Meta:
        verbose_name = _("telemetry ingest")
        verbose_name_plural = _("telemetry ingests")
        ordering = ["-measured_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_owner_tenant_id", "external_reading_id"],
                name="provider_telemetry_source_reading_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["source_owner_tenant_id", "external_reading_id"]),
            models.Index(fields=["external_device", "measured_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_owner_tenant_id}:{self.external_reading_id}"


class B2BIdempotencyKey(models.Model):
    """Cached response for idempotent provider inbound write endpoints."""

    key = models.CharField(max_length=255, verbose_name=_("key"))
    endpoint = models.CharField(max_length=255, verbose_name=_("endpoint"))
    request_hash = models.CharField(max_length=64, verbose_name=_("request hash"))
    response_status = models.PositiveIntegerField(verbose_name=_("response status"))
    response_body = models.JSONField(default=dict, verbose_name=_("response body"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("B2B idempotency key")
        verbose_name_plural = _("B2B idempotency keys")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["key", "endpoint"],
                name="provider_b2b_idempotency_key_endpoint_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["key", "endpoint"]),
        ]

    def __str__(self) -> str:
        return f"{self.endpoint}:{self.key}"
