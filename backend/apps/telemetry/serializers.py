"""
Telemetry serializers.

Handles validation and serialization for the telemetry ingest API.
"""

from rest_framework import serializers

from apps.telemetry.models import TelemetryRecord


class TelemetryReadingSerializer(serializers.Serializer):
    """Single sensor reading within a batch ingest request."""

    sensor_key = serializers.CharField(
        max_length=50,
        help_text="Machine-readable sensor type key (e.g., 'soil_moisture').",
    )
    value = serializers.FloatField(
        help_text="Measured value from the sensor.",
    )
    unit = serializers.CharField(
        max_length=30,
        required=False,
        default="",
        help_text="Unit of measurement (informational, not validated).",
    )


class TelemetryIngestSerializer(serializers.Serializer):
    """
    Serializer for the telemetry ingest endpoint.

    Validates the full payload from a device, including multiple
    sensor readings in a single request.

    Payload format:
    {
        "schema_version": "1.0.0",
        "message_id": "uuid",
        "timestamp": "2026-05-08T14:30:00Z",
        "firmware_version": "2.1.3",
        "readings": [
            {"sensor_key": "soil_moisture", "value": 42.5, "unit": "percent"},
            ...
        ]
    }
    """

    schema_version = serializers.CharField(
        max_length=10,
        help_text="Schema version for forward compatibility.",
    )
    message_id = serializers.CharField(
        max_length=100,
        help_text="Idempotency key for deduplication.",
    )
    timestamp = serializers.DateTimeField(
        help_text="ISO 8601 timestamp from the device clock.",
    )
    firmware_version = serializers.CharField(
        max_length=50,
        required=False,
        default="",
        help_text="Device firmware version at time of reading.",
    )
    readings = TelemetryReadingSerializer(
        many=True,
        help_text="Array of sensor readings.",
    )


class TelemetryRecordSerializer(serializers.ModelSerializer):
    """Read-only serializer for TelemetryRecord retrieval."""

    sensor_key = serializers.CharField(source="sensor_type.key", read_only=True)
    device_id = serializers.CharField(source="device.device_id", read_only=True)

    class Meta:
        model = TelemetryRecord
        fields = [
            "id",
            "device_id",
            "sensor_key",
            "value",
            "measured_at",
            "received_at",
            "message_id",
            "firmware_version",
            "is_valid",
            "validation_error",
        ]
        read_only_fields = fields
