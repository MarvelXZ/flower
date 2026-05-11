from rest_framework import serializers


class LocationUpsertSerializer(serializers.Serializer):
    source_owner_tenant_id = serializers.CharField(max_length=120)
    external_id = serializers.CharField(max_length=120)
    name = serializers.CharField(max_length=180)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        default=None,
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        default=None,
    )
    raw_payload = serializers.JSONField(required=False, default=dict)


class DeviceUpsertSerializer(serializers.Serializer):
    source_owner_tenant_id = serializers.CharField(max_length=120)
    external_id = serializers.CharField(max_length=120)
    external_location_id = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
        allow_null=True,
        default=None,
    )
    name = serializers.CharField(max_length=180)
    status = serializers.CharField(max_length=64)
    raw_payload = serializers.JSONField(required=False, default=dict)


class TelemetryReadingSerializer(serializers.Serializer):
    external_device_id = serializers.CharField(max_length=120)
    external_reading_id = serializers.CharField(max_length=120)
    measured_at = serializers.DateTimeField()
    soil_moisture = serializers.FloatField(required=False, allow_null=True, default=None)
    temperature = serializers.FloatField(required=False, allow_null=True, default=None)
    air_humidity = serializers.FloatField(required=False, allow_null=True, default=None)
    light_level = serializers.FloatField(required=False, allow_null=True, default=None)
    battery_level = serializers.FloatField(required=False, allow_null=True, default=None)
    raw_payload = serializers.JSONField(required=False, default=dict)


class TelemetryBatchSerializer(serializers.Serializer):
    schema_version = serializers.CharField(max_length=10)
    source_owner_tenant_id = serializers.CharField(max_length=120)
    items = TelemetryReadingSerializer(many=True, allow_empty=False, source="readings")

    def validate_schema_version(self, value):
        if value != "1.0":
            raise serializers.ValidationError("Unsupported schema_version.")
        return value
