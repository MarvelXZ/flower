# MQTT Contract

Flower accepts telemetry from ESP32-class devices through MQTT. Phase 2 defines the contract and an ingest service skeleton; it does not introduce a long-running MQTT client process.

## Topic

```text
devices/{device_uuid}/telemetry
```

`device_uuid` must be the UUID assigned by the owner tenant device registry. The same UUID must appear in the payload.

## Payload

Payloads are JSON objects.

Required fields:

- `schema_version`: currently `1.0`
- `device_uuid`: UUID string matching the topic
- `measured_at`: ISO 8601 timestamp

Optional measurement fields:

- `soil_moisture`: numeric percentage
- `temperature`: numeric Celsius value
- `air_humidity`: numeric percentage
- `light_level`: numeric lux/value from the device sensor
- `battery_level`: numeric percentage

At least one measurement field is required.

## Validation

- Topic must match `devices/{device_uuid}/telemetry`.
- `schema_version` must be exactly `1.0`.
- Topic UUID and payload UUID must match.
- `device_uuid` must resolve to a known device in the current owner tenant context.
- `measured_at` must parse as a datetime.
- The telemetry service verifies the device belongs to the current owner tenant schema before writing.

Invalid payloads fail closed. Unknown devices fail closed.

## Example

```json
{
  "schema_version": "1.0",
  "device_uuid": "4fbfe8b7-2ef3-4c9f-8617-6ef4d6828797",
  "measured_at": "2026-05-11T10:05:00Z",
  "soil_moisture": 42.5,
  "temperature": 23.1,
  "air_humidity": 55.0,
  "light_level": 300,
  "battery_level": 87
}
```
