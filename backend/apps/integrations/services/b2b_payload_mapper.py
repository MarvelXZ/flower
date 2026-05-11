from dataclasses import dataclass, field


class UnsupportedOutboxEvent(ValueError):
    """Raised when an outbox event has no provider B2B mapping."""


class InvalidOutboxPayload(ValueError):
    """Raised when an outbox payload cannot produce a provider request."""


@dataclass(frozen=True)
class ProviderB2BRequest:
    method: str
    endpoint: str
    payload: dict
    idempotency_key: str
    headers: dict = field(default_factory=dict)
    body_bytes: bytes | None = None


def _require(payload: dict, key: str):
    value = payload.get(key)
    if value in (None, ""):
        raise InvalidOutboxPayload(f"Missing required outbox payload field: {key}.")
    return value


def map_outbox_event_to_provider_request(event) -> ProviderB2BRequest:
    """Map an owner outbox event to the provider inbound B2B contract."""
    if event.event_type != "SensorReadingReceived":
        raise UnsupportedOutboxEvent(f"Unsupported outbox event_type: {event.event_type}.")

    payload = event.payload or {}
    source_owner_tenant_id = _require(payload, "source_owner_tenant_id")
    external_device_id = _require(payload, "device_uuid")
    external_reading_id = payload.get("sensor_reading_id") or str(event.aggregate_id)
    measured_at = _require(payload, "measured_at")

    return ProviderB2BRequest(
        method="POST",
        endpoint="/api/b2b/v1/telemetry/batch/",
        idempotency_key=str(event.idempotency_key),
        payload={
            "schema_version": "1.0",
            "source_owner_tenant_id": source_owner_tenant_id,
            "items": [
                {
                    "external_reading_id": str(external_reading_id),
                    "external_device_id": str(external_device_id),
                    "measured_at": measured_at,
                    "soil_moisture": payload.get("soil_moisture"),
                    "temperature": payload.get("temperature"),
                    "air_humidity": payload.get("air_humidity"),
                    "light_level": payload.get("light_level"),
                    "battery_level": payload.get("battery_level"),
                }
            ],
        },
    )
