from django.db import connection, transaction
from django.utils import timezone

from apps.provider_ops.models import ExternalDevice, ExternalLocation, TelemetryIngest


class ProviderInboundError(ValueError):
    """Base error for provider inbound service failures."""


class ProviderTenantContextError(ProviderInboundError):
    """Raised when inbound data is handled outside a provider tenant schema."""


class SourceOwnerMismatchError(ProviderInboundError):
    """Raised when the payload ``source_owner_tenant_id`` does not match
    the authenticated key's binding."""


class UnknownExternalLocationError(ProviderInboundError):
    """Raised when a device references an unknown external location."""


class UnknownExternalDeviceError(ProviderInboundError):
    """Raised when telemetry references an unknown external device."""


def _ensure_provider_tenant_context() -> None:
    schema_name = getattr(connection, "schema_name", "")
    if not schema_name or schema_name == "public":
        raise ProviderTenantContextError("Provider inbound API must run in a provider tenant schema.")


def validate_source_owner_id(
    *,
    auth_source_owner_tenant_id: str | None,
    payload_source_owner_tenant_id: str,
) -> str:
    """Return the effective ``source_owner_tenant_id`` to use.

    When an HMAC-authenticated request carries ``auth_source_owner_tenant_id``
    (from the key registry), the payload value **must** match it.  This
    prevents a provider from claiming data from an owner tenant they are
    not authorised for.

    When *no* auth context is available (e.g. test API key path), the
    payload value is used as-is.
    """
    if auth_source_owner_tenant_id and payload_source_owner_tenant_id != auth_source_owner_tenant_id:
        raise SourceOwnerMismatchError(
            f"Payload source_owner_tenant_id '{payload_source_owner_tenant_id}' "
            f"does not match authenticated key binding "
            f"'{auth_source_owner_tenant_id}'.",
        )
    return auth_source_owner_tenant_id or payload_source_owner_tenant_id
    schema_name = getattr(connection, "schema_name", "")
    if not schema_name or schema_name == "public":
        raise ProviderTenantContextError("Provider inbound API must run in a provider tenant schema.")


def upsert_external_location(
    *,
    source_owner_tenant_id: str,
    external_id: str,
    name: str,
    address: str = "",
    latitude=None,
    longitude=None,
    raw_payload: dict | None = None,
):
    """Create or update a provider-side owner location copy."""
    _ensure_provider_tenant_context()
    payload = raw_payload or {}

    with transaction.atomic():
        location, created = ExternalLocation.objects.update_or_create(
            source_owner_tenant_id=source_owner_tenant_id,
            external_id=external_id,
            defaults={
                "name": name,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
                "raw_payload": payload,
                "last_synced_at": timezone.now(),
            },
        )

    return location, created


def upsert_external_device(
    *,
    source_owner_tenant_id: str,
    external_id: str,
    name: str,
    status: str,
    external_location_id: str | None = None,
    raw_payload: dict | None = None,
):
    """Create or update a provider-side owner device copy."""
    _ensure_provider_tenant_context()
    payload = raw_payload or {}
    external_location = None

    with transaction.atomic():
        if external_location_id:
            try:
                external_location = ExternalLocation.objects.get(
                    source_owner_tenant_id=source_owner_tenant_id,
                    external_id=external_location_id,
                )
            except ExternalLocation.DoesNotExist as exc:
                raise UnknownExternalLocationError("Unknown external_location_id.") from exc

        device, created = ExternalDevice.objects.update_or_create(
            source_owner_tenant_id=source_owner_tenant_id,
            external_id=external_id,
            defaults={
                "external_location": external_location,
                "name": name,
                "status": status,
                "raw_payload": payload,
                "last_synced_at": timezone.now(),
            },
        )

    return device, created


def ingest_telemetry_batch(*, source_owner_tenant_id: str, readings: list[dict]):
    """Idempotently ingest provider-side telemetry copies."""
    _ensure_provider_tenant_context()
    ingested = []

    with transaction.atomic():
        for reading in readings:
            try:
                external_device = ExternalDevice.objects.get(
                    source_owner_tenant_id=source_owner_tenant_id,
                    external_id=reading["external_device_id"],
                )
            except ExternalDevice.DoesNotExist as exc:
                raise UnknownExternalDeviceError("Unknown external_device_id.") from exc

            ingest, _created = TelemetryIngest.objects.update_or_create(
                source_owner_tenant_id=source_owner_tenant_id,
                external_reading_id=reading["external_reading_id"],
                defaults={
                    "external_device": external_device,
                    "measured_at": reading["measured_at"],
                    "soil_moisture": reading.get("soil_moisture"),
                    "temperature": reading.get("temperature"),
                    "air_humidity": reading.get("air_humidity"),
                    "light_level": reading.get("light_level"),
                    "battery_level": reading.get("battery_level"),
                    "raw_payload": reading.get("raw_payload") or reading,
                },
            )
            ingested.append(ingest)

    return ingested
