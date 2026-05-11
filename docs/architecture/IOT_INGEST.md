# IoT Ingest

ESP32 devices publish telemetry through MQTT using the contract in [MQTT_CONTRACT.md](MQTT_CONTRACT.md).

The MQTT ingest skeleton is a service, not a broker client. It parses the topic, validates the payload, resolves the device, and delegates all writes to `apps.telemetry.services.sensor_reading_service.record_sensor_reading`.

Phase 11 adds rule evaluation during sensor reading ingest —
see [Rule & Alert Engine](RULE_ALERT_ENGINE.md).

The first durable write for a valid telemetry payload is an owner-schema `SensorReading`. The service then updates `Device.last_seen_at` and creates a tenant-local `IntegrationOutbox` event of type `SensorReadingReceived` in the same database transaction.

The service validates that `Device.owner_tenant_schema` matches the current django-tenants schema before writing. This preserves the owner tenant as the canonical source of truth and prevents provider-context writes.

Phase 2 does not implement provider forwarding, MQTT client lifecycle management, Celery delivery workers, or B2B sync.
