# Provider Task Workflow

Phase 14 adds the provider-side task workflow that converts alert events
into operational maintenance tasks.  Tasks live in the provider tenant
schema and reference owner data through external IDs only.

## Architecture

```
Owner tenant                              Provider tenant
─────────────────                         ─────────────────

SensorReading                             ProviderTask
  │                                         │
  ├── evaluate_sensor_reading()             ├── task_key (idempotency)
  │     └── Alert (open)                   ├── source_owner_tenant_id
  │                                         ├── external_alert_id
  ▼                                         ├── external_location_id
IntegrationOutbox                          ├── external_plant_id
  │                                         ├── external_device_id
  └── deliver_outbox_event()                ├── task_type / priority / status
        │                                   ├── events [ProviderTaskEvent]
        ▼                                   └── notes [ProviderTaskNote]
  Provider inbound B2B API
    POST /api/b2b/v1/alerts/upsert/
      │
      ├── map_alert_to_task_payload()   ← rule_code → task_type
      ├── validate_source_owner_id()    ← auth context check
      └── create_task()                 ← idempotent per task_key
```

## Task Lifecycle

```
OPEN ──→ ASSIGNED ──→ IN_PROGRESS ──→ COMPLETED (terminal)
  │                      │
  ├──→ CANCELLED (term)  └──→ CANCELLED (terminal)
  └──→ IN_PROGRESS (skip assign)
```

| From | To | Allowed? |
|------|----|----------|
| open | assigned | ✅ |
| open | in_progress | ✅ |
| open | cancelled | ✅ |
| assigned | in_progress | ✅ |
| assigned | cancelled | ✅ |
| in_progress | completed | ✅ |
| in_progress | cancelled | ✅ |
| completed | anything | ❌ (terminal) |
| cancelled | anything | ❌ (terminal) |

## Alert → Task Mapping

| Rule code | Task type |
|-----------|-----------|
| `soil_moisture_low` | `watering` |
| `soil_moisture_high` | `inspection` |
| `temperature_low/high` | `inspection` |
| `air_humidity_low/high` | `inspection` |
| `battery_low` | `device_check` |
| `device_offline` | `device_check` |
| (default) | `maintenance` |

| Alert severity | Task priority |
|----------------|---------------|
| `critical` | `urgent` |
| `warning` | `high` |
| `info` | `normal` |

## Idempotency

- **`task_key`** = `"{source_owner_tenant_id}:{external_alert_id}:{task_type}"`
- `create_task()` je idempotentan: isti `task_key` vraća postojeći task
- Duplikati se ne prave ni za isti alert payload

## Models

All live in the provider tenant schema (`provider_ops`):

### ProviderTask

| Field | Purpose |
|-------|---------|
| `task_key` | Idempotency key (unique) |
| `source_owner_tenant_id` | Owner that originated the alert |
| `external_*_id` | Owner-side references (no FKs to owner schema) |
| `task_type` | `inspection` / `watering` / `device_check` / etc. |
| `priority` | `low` / `normal` / `high` / `urgent` |
| `status` | `open` → `assigned` → `in_progress` → `completed` / `cancelled` |

### ProviderTaskEvent

Audit trail — one event per status transition.

### ProviderTaskNote

Free-text notes attached to a task.

## Provider Dashboard API

All endpoints live under `/api/provider/tasks/`:

| Method | Path | Action |
|--------|------|--------|
| GET | `/api/provider/tasks/` | List open tasks + dashboard summary |
| GET | `/api/provider/tasks/{id}/` | Task detail with events and notes |
| POST | `/api/provider/tasks/{id}/assign/` | Assign to worker |
| POST | `/api/provider/tasks/{id}/start/` | Start work |
| POST | `/api/provider/tasks/{id}/complete/` | Complete with optional note |
| POST | `/api/provider/tasks/{id}/cancel/` | Cancel with reason |
| POST | `/api/provider/tasks/{id}/notes/` | Add a note |

## Provider Inbound Alert Endpoint

`POST /api/b2b/v1/alerts/upsert/` — HMAC-authenticated B2B endpoint that
accepts an alert payload from the owner and creates a task on the provider
side.

- Source owner must match the auth context
- Uses `alert_task_mapper` to derive task type and priority
- Creates task via `task_service.create_task()` (idempotent)

## Task Notifications

Task creation notifications are **not yet implemented**.  A future phase
will add `task_created` notification types and enqueue them through the
existing `NotificationOutbox` pipeline.

Phase 15 adds SLA & escalation — see [SLA & Escalation Engine](SLA_ESCALATION_ENGINE.md).
Phase 16 adds the mobile-ready dashboard API — see [Mobile-ready API](MOBILE_READY_API.md).

## Why No Direct Owner Schema Reads

Provider tasks reference owner data through `external_*_id` fields —
strings, not foreign keys.  This maintains tenant isolation: the provider
never queries the owner schema directly.

## Files

| File | Purpose |
|------|---------|
| `provider_ops/domain/enums.py` | ProviderTaskType, Priority, Status, EventType |
| `provider_ops/models/task.py` | ProviderTask, ProviderTaskEvent, ProviderTaskNote |
| `provider_ops/services/task_service.py` | Task lifecycle service |
| `provider_ops/services/alert_task_mapper.py` | Alert → task mapping |
| `provider_ops/selectors/task_selectors.py` | Task read queries |
| `provider_ops/api/serializers/task.py` | API serializers |
| `provider_ops/api/views/task.py` | API views (B2B + dashboard) |
| `provider_ops/api/urls.py` | URL routing |
