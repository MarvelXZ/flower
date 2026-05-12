# Device Control Plane

Phase 10 implements the full device fleet management layer — the
foundation that turns Flower from a SaaS platform into a true enterprise
IoT platform.

## Motivation

The platform already has:
- Multi-tenant architecture (django-tenants, schema-per-tenant)
- B2B provider integration (HMAC, outbox, sync engine)
- IoT sensor ingest foundation (MQTT, telemetry models)
- Firmware version tracking

What it needs to become a production IoT platform:

1. **Device registry & provisioning** — lifecycle from factory to active.
2. **Per-device security** — credentials, secrets, MQTT ACL.
3. **Heartbeat & offline detection** — fleet health monitoring.
4. **Device shadow** — desired vs reported state synchronisation.
5. **OTA firmware rollout** — staged, canary, checksum-verified.
6. **MQTT topic ACL** — tenant isolation, anti-spoofing.

## Architecture

```
                    ┌──────────────────────────┐
                    │    Device Control Plane   │
                    │                          │
                    │  ┌──────────────────────┐ │
                    │  │   Device Registry     │ │
                    │  │   (serial, revision,  │ │
                    │  │    capabilities, MQTT) │ │
                    │  └──────────┬───────────┘ │
                    │             │             │
                    │  ┌──────────▼───────────┐ │
                    │  │   Provisioning        │ │
                    │  │   (credentials,        │ │
                    │  │    lifecycle states)   │ │
                    │  └──────────┬───────────┘ │
                    │             │             │
                    │  ┌──────────▼───────────┐ │
                    │  │   Device Shadow       │ │
                    │  │   (desired/reported,   │ │
                    │  │    delta computation)  │ │
                    │  └──────────┬───────────┘ │
                    │             │             │
                    │  ┌──────────▼───────────┐ │
                    │  │   MQTT ACL            │ │
                    │  │   (tenant isolation,   │ │
                    │  │    anti-spoofing)      │ │
                    │  └──────────────────────┘ │
                    └──────────────────────────┘
```

## Models

### Device

Extended with full hardware and software identity:

| Field | Purpose |
|-------|---------|
| `serial_number` | Factory-assigned hardware serial (unique) |
| `hardware_revision` | Board revision for OTA compatibility checks |
| `firmware_version` | Currently running firmware version |
| `mqtt_client_id` | Canonical MQTT client identifier |
| `capabilities` | JSON list (e.g. `["temperature", "humidity"]`) |
| `provisioning_status` | Lifecycle stage |
| `heartbeat_interval_seconds` | Expected heartbeat cadence |
| `last_ip` | Last known IP address |

### DeviceHeartbeat (append-only)

Every heartbeat is a new row — never overwritten.  This preserves a
full audit trail of device connectivity.  The most recent heartbeat is
derived via `SELECT ... ORDER BY received_at DESC LIMIT 1`.

### DeviceShadow

Cloud-side state synchronisation using the IoT shadow pattern:

- **Desired** — what the cloud wants the device to converge to (e.g. firmware target, config).
- **Reported** — what the device says its state is.
- **delta** = `desired.keys - reported.keys` where values differ.

The delta drives:
- OTA update triggers (desired firmware != reported firmware)
- Configuration pushes
- Command delivery

### DeviceCredential

Per-device HMAC credentials.  `api_secret_hash` stores an Argon2 hash
of the shared secret — the plaintext is NEVER persisted and is returned
only once during provisioning for secure delivery.

### FirmwareVersion — extended

| Field | Purpose |
|-------|---------|
| `checksum_sha256` | Hex-encoded SHA-256 of binary |
| `artifact_url` | External CDN URL (optional) |
| `minimum_hardware_revision` | Prevents incompatible OTA |
| `rollout_stage` | `canary → staged → full` |

### FirmwareDeployment

Tracks per-device OTA deployment with full lifecycle state machine:

```
pending → downloading → flashing → rebooting → completed
                                                failed
```

## Provisioning Lifecycle

```
UNPROVISIONED → IDENTITY_CREATED → CERTIFICATE_ISSUED → REGISTERED → ACTIVATED
```

1. **UNPROVISIONED** — device registered but no credentials.
2. **IDENTITY_CREATED** — `DeviceCredential` generated, secret ready for delivery.
3. **CERTIFICATE_ISSUED** — MQTT certificate issued (future phase).
4. **REGISTERED** — device fully provisioned, waiting for activation.
5. **ACTIVATED** — device is live and sending data.

## MQTT Topic Structure

```
tenant/{tenant_schema}/device/{device_serial}/telemetry      (publish)
tenant/{tenant_schema}/device/{device_serial}/heartbeat      (publish)
tenant/{tenant_schema}/device/{device_serial}/shadow/reported (publish)
tenant/{tenant_schema}/device/{device_serial}/shadow/desired (subscribe)
tenant/{tenant_schema}/device/{device_serial}/ota/status     (publish)
tenant/{tenant_schema}/device/{device_serial}/ota/update     (subscribe)
tenant/{tenant_schema}/device/{device_serial}/cmd            (subscribe)
```

## MQTT ACL Rules

### Device Publish (device → cloud)

Allowed: `telemetry`, `heartbeat`, `shadow/reported`, `ota/status`

Forbidden: anything else, including `shadow/desired`

### Device Subscribe (cloud → device)

Allowed: `shadow/desired`, `ota/update`, `cmd`

Forbidden: everything else, including `telemetry`

### Tenant Isolation

A device can only:
- Publish to `tenant/{its_own_tenant}/device/{its_own_serial}/*`
- Subscribe to `tenant/{its_own_tenant}/device/{its_own_serial}/*`

Any cross-tenant or cross-device topic access raises `TenantIsolationError`
or `DeviceSpoofingError`.

## Offline Detection

Devices are flagged as offline when:
`now - last_seen_at > heartbeat_interval_seconds * max_missed_heartbeats`

The `detect_offline_devices()` function scans active devices and returns
those that have exceeded their heartbeat window.  A Celery periodic task
should call this every 60 seconds and emit `DeviceOffline` events.

## OTA Rollout Strategy

```
canary (1-2 devices) → staged (X% of fleet) → full (all compatible)
```

- `canary` — initial validation on test devices.
- `staged` — gradual rollout, monitoring failure rate.
- `full` — available to all devices with compatible hardware.

The `minimum_hardware_revision` on `FirmwareVersion` prevents deployment
to incompatible hardware.

## Broker Recommendation

**Mosquitto** is fine for development and small fleets (< 100 devices).

For production at scale, migrate to **EMQX** or **HiveMQ CE**:

| Feature | Mosquitto | EMQX |
|---------|-----------|------|
| Clustering | ❌ (bridge only) | ✅ built-in |
| JWT Auth | ❌ (plugin) | ✅ built-in |
| ACL | Static file | Database / HTTP API |
| WebSocket | ✅ | ✅ |
| Rule Engine | ❌ | ✅ SQL-based |
| Observability | Minimal | Prometheus + Dashboard |
| License | EPL-2.0 | Business Source (free tier) |
