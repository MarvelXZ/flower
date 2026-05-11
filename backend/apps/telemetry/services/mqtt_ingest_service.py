from datetime import UTC
from uuid import UUID

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.devices.models import Device
from apps.telemetry.services.sensor_reading_service import record_sensor_reading


EXPECTED_SCHEMA_VERSION = "1.0"
TOPIC_PREFIX = "devices"
TOPIC_SUFFIX = "telemetry"
MEASUREMENT_FIELDS = (
    "soil_moisture",
    "temperature",
    "air_humidity",
    "light_level",
    "battery_level",
)


class TelemetryIngestError(ValueError):
    """Base fail-closed ingest error."""


class InvalidTelemetryPayloadError(TelemetryIngestError):
    """Raised when MQTT payload validation fails."""


class UnknownDeviceError(TelemetryIngestError):
    """Raised when the payload references an unknown device."""


def _parse_topic_device_uuid(topic: str) -> UUID:
    parts = topic.split("/")
    if len(parts) != 3 or parts[0] != TOPIC_PREFIX or parts[2] != TOPIC_SUFFIX:
        raise InvalidTelemetryPayloadError("Invalid MQTT telemetry topic.")

    try:
        return UUID(parts[1])
    except ValueError as exc:
        raise InvalidTelemetryPayloadError("Invalid device UUID in MQTT topic.") from exc


def _parse_measured_at(value: str):
    measured_at = parse_datetime(value) if isinstance(value, str) else None
    if measured_at is None:
        raise InvalidTelemetryPayloadError("Invalid measured_at timestamp.")
    if timezone.is_naive(measured_at):
        measured_at = timezone.make_aware(measured_at, timezone=UTC)
    return measured_at


def _validate_payload(topic_device_uuid: UUID, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise InvalidTelemetryPayloadError("MQTT telemetry payload must be a JSON object.")

    if payload.get("schema_version") != EXPECTED_SCHEMA_VERSION:
        raise InvalidTelemetryPayloadError("Unsupported telemetry schema_version.")

    try:
        payload_device_uuid = UUID(str(payload["device_uuid"]))
    except (KeyError, ValueError) as exc:
        raise InvalidTelemetryPayloadError("Invalid or missing device_uuid.") from exc

    if payload_device_uuid != topic_device_uuid:
        raise InvalidTelemetryPayloadError("Topic device UUID and payload device_uuid do not match.")

    if "measured_at" not in payload:
        raise InvalidTelemetryPayloadError("Missing measured_at.")

    measurements = {field: payload.get(field) for field in MEASUREMENT_FIELDS}
    if all(value is None for value in measurements.values()):
        raise InvalidTelemetryPayloadError("At least one measurement field is required.")

    return {
        "device_uuid": payload_device_uuid,
        "measured_at": _parse_measured_at(payload["measured_at"]),
        **measurements,
    }


def ingest_telemetry_payload(topic: str, payload: dict):
    """Validate an MQTT telemetry payload and delegate owner-context writes."""
    topic_device_uuid = _parse_topic_device_uuid(topic)
    validated = _validate_payload(topic_device_uuid, payload)

    try:
        device = Device.objects.get(uuid=validated["device_uuid"])
    except Device.DoesNotExist as exc:
        raise UnknownDeviceError("Unknown device_uuid.") from exc

    return record_sensor_reading(
        device=device,
        measured_at=validated["measured_at"],
        soil_moisture=validated["soil_moisture"],
        temperature=validated["temperature"],
        air_humidity=validated["air_humidity"],
        light_level=validated["light_level"],
        battery_level=validated["battery_level"],
    )
