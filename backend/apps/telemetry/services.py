"""
Telemetry write operations (services layer).

All mutations to telemetry data MUST go through this module.
Direct model writes outside of services are prohibited.

NOTE: Telemetry records are append-only. There are no updates or deletes.
"""

import logging

from django.db import IntegrityError

from apps.telemetry.models import SensorType, TelemetryRecord

logger = logging.getLogger(__name__)


def ingest_telemetry(*, device, payload):
    """
    Process an incoming telemetry payload from a device.

    For each reading in the payload:
    1. Look up the SensorType by key
    2. Validate the value against SensorType min/max
    3. Deduplicate using message_id + sensor_key
    4. Persist as TelemetryRecord (append-only)

    Returns a dict with processed/skipped/errors counts.
    """
    message_id = payload["message_id"]
    measured_at = payload["timestamp"]
    firmware_version = payload.get("firmware_version", "")
    readings = payload.get("readings", [])

    processed = 0
    skipped = 0
    errors = []

    for reading in readings:
        sensor_key = reading["sensor_key"]
        value = reading["value"]

        # Look up sensor type
        try:
            sensor_type = SensorType.objects.get(key=sensor_key)
        except SensorType.DoesNotExist:
            errors.append(f"Unknown sensor key: {sensor_key}")
            skipped += 1
            continue

        # Validate value against sensor type bounds
        is_valid = True
        validation_error = ""
        if sensor_type.min_value is not None and value < sensor_type.min_value:
            is_valid = False
            validation_error = f"Value {value} below minimum {sensor_type.min_value}"
        elif sensor_type.max_value is not None and value > sensor_type.max_value:
            is_valid = False
            validation_error = f"Value {value} above maximum {sensor_type.max_value}"

        # Create composite message_id for dedup (one message may have multiple readings)
        composite_message_id = f"{message_id}:{sensor_key}"

        try:
            TelemetryRecord.objects.create(
                device=device,
                sensor_type=sensor_type,
                value=value,
                measured_at=measured_at,
                message_id=composite_message_id,
                raw_payload=reading,
                firmware_version=firmware_version,
                is_valid=is_valid,
                validation_error=validation_error,
            )
            processed += 1
        except IntegrityError:
            # Duplicate message_id — skip silently (idempotent)
            skipped += 1
            logger.debug(
                "Duplicate telemetry skipped: device=%s message_id=%s sensor=%s",
                device.device_id,
                composite_message_id,
                sensor_key,
            )

    return {
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
    }
