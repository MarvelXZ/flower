# IoT Ingest Pipeline

This document describes the data flow from ESP32 devices to actionable tasks.

## Pipeline Overview

```
ESP32 Device
    |
    v
MQTT / HTTP Ingest
    |
    v
Raw Reading (append-only)
    |
    v
Processing / Validation
    |
    v
Snapshot (aggregated view)
    |
    v
Alert Evaluation
    |
    v
Task Generation
    |
    v
Notification Dispatch
```

## Stages

### 1. ESP32 Device
- Collects sensor data: soil moisture, temperature, light, battery.
- Sends payloads via MQTT or HTTP POST.
- Device has a unique hardware serial (device_id).

### 2. Ingest Endpoint
- Accepts raw payloads from devices.
- Validates API key / device token.
- Stores the raw payload immediately.
- Returns 202 Accepted (async processing).

### 3. Raw Reading (append-only)
- Table: `measurements_rawreading`
- Fields: device_id, sensor_type, value, unit, measured_at, received_at, raw_payload
- **CRITICAL**: Raw readings are append-only. Never update or delete.

### 4. Processing
- Celery task processes raw readings.
- Validates range, deduplicates, handles time drift.
- Produces a processed snapshot.

### 5. Snapshot
- Aggregated view per device / per hour.
- Used for dashboards and analytics.

### 6. Alert Evaluation
- Compares snapshot values against plant care thresholds.
- If threshold is breached, creates an alert.
- **CRITICAL**: Alert events are append-only.

### 7. Task Generation
- High-severity alerts spawn tasks.
- Tasks are assigned to gardeners/workers.

### 8. Notification Dispatch
- Tasks and alerts trigger notifications.
- Channels: email, SMS, push, in-app.

## Key Principles

1. **Devices NEVER write business state directly.**
   - Devices only append raw readings.
   - All business decisions happen in background processing.

2. **Raw readings are append-only.**
   - No updates. No deletes.
   - If bad data arrives, mark it invalid; do not delete.

3. **Processing is idempotent.**
   - Re-running the processor on the same raw reading must not create duplicates.

4. **Alerts are append-only events.**
   - An alert is a fact. It happened.
   - Resolution is a new event, not an update.
