from django.db import connection, transaction

from apps.care_engine.services.rule_evaluation_service import evaluate_sensor_reading
from apps.integrations.domain.enums import OutboxStatus
from apps.integrations.models import IntegrationOutbox
from apps.telemetry.models import SensorReading


class TenantIsolationError(ValueError):
    """Raised when a device is used outside its owner tenant context."""


class RuleEvaluationError(RuntimeError):
    """Raised when rule evaluation fails during sensor reading ingest.

    This is a non-critical error — the sensor reading is still recorded.
    """


def _current_schema_name() -> str:
    return getattr(connection, "schema_name", "")


def _serialize_measured_at(measured_at) -> str:
    if hasattr(measured_at, "isoformat"):
        return measured_at.isoformat()
    return str(measured_at)


def record_sensor_reading(
    *,
    device,
    measured_at,
    soil_moisture=None,
    temperature=None,
    air_humidity=None,
    light_level=None,
    battery_level=None,
) -> SensorReading:
    """Persist an owner-context reading, enqueue outbox, and evaluate rules.

    The sensor reading and outbox event are written atomically.  Rule
    evaluation runs inside the same transaction (fail-closed for MVP).
    See ``docs/architecture/RULE_ALERT_ENGINE.md`` for the rationale.
    """
    current_schema = _current_schema_name()
    if not current_schema or device.owner_tenant_schema != current_schema:
        raise TenantIsolationError("Device does not belong to the current owner tenant context.")

    with transaction.atomic():
        reading = SensorReading.objects.create(
            device=device,
            measured_at=measured_at,
            soil_moisture=soil_moisture,
            temperature=temperature,
            air_humidity=air_humidity,
            light_level=light_level,
            battery_level=battery_level,
        )

        device.last_seen_at = measured_at
        device.save(update_fields=["last_seen_at", "updated_at"])

        IntegrationOutbox.objects.create(
            event_type="SensorReadingReceived",
            aggregate_type="SensorReading",
            aggregate_id=str(reading.pk),
            payload={
                "source_owner_tenant_id": current_schema,
                "sensor_reading_id": str(reading.pk),
                "device_uuid": str(device.uuid),
                "measured_at": _serialize_measured_at(measured_at),
                "soil_moisture": soil_moisture,
                "temperature": temperature,
                "air_humidity": air_humidity,
                "light_level": light_level,
                "battery_level": battery_level,
            },
            status=OutboxStatus.PENDING,
        )

        # Rule evaluation — fail-closed: if the engine crashes, the reading
        # + outbox are rolled back together.  This ensures alert consistency.
        evaluate_sensor_reading(reading)

    return reading
