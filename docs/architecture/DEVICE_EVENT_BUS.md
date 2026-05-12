# Device Event Bus

Phase 10 adds a canonical event backbone for device lifecycle events.
Every provisioning state change, heartbeat, shadow update, and firmware
operation emits a typed `DeviceEvent` through the event bus.

## Motivation

The platform needs a single source of truth for device events so that:

- **Realtime notifications** can push live updates via WebSocket/Redis pub/sub.
- **Alerting engine** can evaluate rules on `device.offline` or `device.heartbeat_received`.
- **Analytics pipeline** can compute device reliability scores from heartbeat history.
- **Automation engine** can trigger workflows on `device.firmware_failed`.
- **Audit trail** preserves a complete timeline of every state transition.

Without a canonical event bus, each subsystem would independently poll
device state — fragile, inconsistent, and slow.

## Event Types

All event types follow the pattern `device.<past_tense_verb>`:

| Event Type | Emitted When |
|-----------|-------------|
| `device.provisioned` | Device registered in the system |
| `device.identity_created` | API credentials generated |
| `device.registered` | Provisioning complete |
| `device.activated` | Device is live and sending data |
| `device.deactivated` | Device retired/decommissioned |
| `device.offline` | Heartbeat window exceeded |
| `device.online` | Device reconnects after offline |
| `device.heartbeat_received` | Append-only heartbeat recorded |
| `device.shadow_reported` | Device reports its state |
| `device.shadow_desired` | Cloud sets desired state |
| `device.firmware_assigned` | OTA update queued for device |
| `device.firmware_download_started` | Device started firmware download |
| `device.firmware_flash_started` | Device started flashing |
| `device.firmware_completed` | OTA update successful |
| `device.firmware_failed` | OTA update failed |
| `device.credential_rotated` | Device credentials rotated |
| `device.provisioning_failed` | Provisioning pipeline failed |

## Architecture

```
Provisioning Service
  │
  ├── _transition()
  │     ├── validate_transition()  ← State Machine
  │     └── record_transition()    ← Audit Trail
  │
  └── _emit_device_event()        ← Event Bus
         │
         └── emit(DeviceEvent)
               │
               ├──→ Subscriber 1 (WebSocket/Redis pub/sub)
               ├──→ Subscriber 2 (Alert Engine)
               ├──→ Subscriber 3 (Analytics)
               └──→ Subscriber N (Custom)
```

## Event Data Class

```python
@dataclass(frozen=True)
class DeviceEvent:
    event_id: str       # UUID4
    event_type: str     # device.<verb>
    device_serial: str
    device_uuid: str
    tenant_schema: str
    timestamp: str      # ISO 8601
    data: dict          # Event-specific payload
    correlation_id: str # For request tracing
```

Events are **immutable** — once emitted, never modified.

## Event Bus API

```python
from apps.devices.events import emit, subscribe, unsubscribe, DeviceEvent

def my_handler(event: DeviceEvent):
    if event.event_type == DeviceEventType.OFFLINE:
        send_alert(event.device_serial)

subscribe(my_handler)
```

Subscribers are called **synchronously** within the same database transaction
as the state change. If a subscriber raises, the error is logged but
subsequent subscribers still execute. No subscriber can block another.

For production, replace the in-process subscriber list with Redis pub/sub
or a message broker (NATS, Redpanda).

## State Machine Enforcement

Every provisioning status transition is validated against a whitelist:

```
UNPROVISIONED ──→ IDENTITY_CREATED ──→ REGISTERED ──→ ACTIVATED
     │                  │                    │              │
     └──→ FAILED        └──→ FAILED          └──→ FAILED    └──→ FAILED
     (terminal)         (terminal)           (terminal)     (terminal)
```

Forbidden transitions:
- `ACTIVATED → UNPROVISIONED` (cannot un-provision live device)
- `ACTIVATED → IDENTITY_CREATED` (cannot downgrade)
- `FAILED → anything` (terminal)
- `IDENTITY_CREATED → ACTIVATED` (must go through REGISTERED)

The state machine lives in `apps/devices/domain/state_machine.py` and is
enforced by `validate_transition()` called from the provisioning service.

## Append-Only Audit Trail

`ProvisioningAuditEntry` records every provisioning state transition:

```
device_id, from_status, to_status, triggered_by, metadata, created_at
```

Rows are never modified or deleted. This is the canonical audit log for:
- Device lifecycle forensics
- SLA computation (time-to-provision, time-to-activate)
- Compliance reporting
- Anomaly detection (unusual transition patterns)
