# Rule & Alert Engine

Phase 11 adds the rule engine that evaluates ``SensorReading`` data and
creates ``Alert`` records — without push notifications, mobile APIs, or
provider task workflows.

## Architecture

```
MQTT / API Ingest
  │
  └── record_sensor_reading()          ← telemetry/services/sensor_reading_service.py
        │
        ├── SensorReading (create)
        ├── IntegrationOutbox (create)
        └── evaluate_sensor_reading()  ← Rule evaluation inside same transaction
              │
              ├── evaluate_soil_moisture()
              ├── evaluate_temperature()
              ├── evaluate_air_humidity()
              └── evaluate_battery()
                    │
                    └── open_or_update_alert()
                          │
                          ├── New alert_key → create Alert (OPEN)
                          └── Existing active alert → update last_seen_at
```

## Rule Codes

Defined in ``care_engine/domain/rule_codes.py``:

| Code | Description |
|------|-------------|
| `soil_moisture_low` | Soil moisture below minimum threshold |
| `soil_moisture_high` | Soil moisture above maximum threshold |
| `temperature_low` | Temperature below minimum |
| `temperature_high` | Temperature above maximum |
| `air_humidity_low` | Air humidity below minimum |
| `air_humidity_high` | Air humidity above maximum |
| `battery_low` | Battery level below minimum |
| `device_offline` | Placeholder — not yet evaluated |

## Default Thresholds

Defined in ``care_engine/domain/thresholds.py``:

| Threshold | Value |
|-----------|-------|
| `SOIL_MOISTURE_MIN` | 20% |
| `SOIL_MOISTURE_MAX` | 80% |
| `TEMPERATURE_MIN` | 5 °C |
| `TEMPERATURE_MAX` | 40 °C |
| `AIR_HUMIDITY_MIN` | 30% |
| `AIR_HUMIDITY_MAX` | 90% |
| `BATTERY_MIN` | 15% |

Future phases will allow per-plant overrides via ``PlantCareProfile``.

## Alert Lifecycle

```
OPEN ──→ ACKNOWLEDGED ──→ RESOLVED  (terminal)
  │          │
  ├──────────┴──→ DISMISSED (terminal)
```

| Transition | Allowed? |
|------------|----------|
| `open` → `acknowledged` | ✅ |
| `open` → `resolved` | ✅ |
| `open` → `dismissed` | ✅ |
| `acknowledged` → `resolved` | ✅ |
| `acknowledged` → `dismissed` | ✅ |
| `resolved` → anything | ❌ (terminal) |
| `dismissed` → anything | ❌ (terminal) |

## Idempotency

- **Per `alert_key`**: while an alert is `open` or `acknowledged`, repeated
  evaluations with the same key update `last_seen_at` and `metadata` instead
  of creating a duplicate.
- Once an alert is `resolved` or `dismissed` (terminal), a new occurrence of
  the same condition creates a **new alert instance** — the old one is
  immutable.
- The `alert_key` format is `"{rule_code}:device_{device_id}"`.

## Alert Model

``Alert`` lives in ``notifications/models/alert.py`` (tenant schema).

| Field | Purpose |
|-------|---------|
| `alert_key` | Deduplication key — unique while open/acknowledged |
| `source_type` | `sensor_reading` / `device` / `plant` / `system` |
| `source_id` | ID of the source record |
| `severity` | `info` / `warning` / `critical` |
| `status` | `open` / `acknowledged` / `resolved` / `dismissed` |
| `plant` / `device` / `sensor_reading` | Optional FK links |
| `rule_code` | The rule that triggered this alert |
| `first_seen_at` / `last_seen_at` | Occurrence window |
| `metadata` | JSON blob with reading values, thresholds, etc. |

### Migration Safety Note

The model-level defaults (`alert_key=""`, `first_seen_at=timezone.now`,
`last_seen_at=timezone.now`, `source_id=""`, `rule_code=""`) exist **only**
to make the schema migration non-interactive.  Runtime alert identity,
timestamps, and business values are always set by the service layer —
never by model defaults.  Legacy rows populated by these defaults would
lack meaningful alert keys and should be cleaned up if they exist.

## Telemetry Integration

Rule evaluation is called **inside the same transaction** as
``record_sensor_reading()``.  This is a deliberate **fail-closed** design
choice for MVP:

- Sensor reading + outbox + alerts are committed or rolled back together.
- If the rule engine crashes, the reading never materialises — ensuring
  alert consistency.
- Documented in `docs/architecture/RULE_ALERT_ENGINE.md` for future
  architecture reviews.

## Alert Outbox Events

Phase 12 implements notification delivery — see [Notification Delivery](NOTIFICATION_DELIVERY.md).

Phase 14 adds provider task workflow — see [Provider Task Workflow](PROVIDER_TASK_WORKFLOW.md).

## Files

| File | Purpose |
|------|---------|
| `notifications/models/alert.py` | Alert model |
| `notifications/domain/enums.py` | AlertSeverity, AlertStatus, AlertSourceType |
| `notifications/services/alert_service.py` | Alert lifecycle service |
| `care_engine/domain/rule_codes.py` | Rule code enum |
| `care_engine/domain/thresholds.py` | Default threshold constants |
| `care_engine/services/rule_evaluation_service.py` | Rule evaluation engine |
| `telemetry/services/sensor_reading_service.py` | Integration point |
