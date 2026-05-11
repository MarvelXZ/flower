# Realtime & Mobile Runtime

Phase 18 adds the production-grade realtime runtime layer for the provider
dashboard and future mobile applications.

## Realtime Architecture

```
Mobile / Web Client
  │
  ├── WebSocket  ──→ ws/provider/v1/dashboard/?token=<JWT>
  │     │
  │     ├── Tenant-scoped channel group
  │     ├── Replay on reconnect (last_event_id)
  │     └── Heartbeat (ping/pong)
  │
  ├── REST API    ──→ /api/provider/v1/dashboard/delta/?since=<ts>
  │     │
  │     └── Polling fallback for environments without WS
  │
  └── REST API    ──→ /api/provider/v1/realtime/replay/?after=<id>
        │
        └── Reconnect resume (event store)
```

## Component Diagram

```
Task Service ──→ publish_task_event()
                     │
SLA Service  ──→ publish_sla_event()  ──→ RealtimeEvent (DB store)
                     │
Notification ──→ publish_event()           │
                                           ├── broadcast (Channels) ──→ WS client
                                           └── replay (REST)       ──→ REST client
```

## JWT / Session Strategy

| Component | Technology |
|-----------|------------|
| Token issuance | `POST /api/auth/v1/token/` |
| Token refresh | `POST /api/auth/v1/token/refresh/` |
| Token format | JWT (access + refresh) |
| Access TTL | Short-lived (default 5 min) |
| Refresh rotation | Enabled (each refresh issues new refresh token) |
| Revocation | `MobileSession.revoke()` on logout |
| Blacklist | `MobileSession.is_active` flag |

### JWT Payload

```json
{
    "user_id": 42,
    "tenant_schema": "provider_1",
    "role": "provider_worker",
    "session_id": "jti-uuid",
    "exp": 1715000000
}
```

## WebSocket Protocol

### Connect

```
→ ws://host/ws/provider/v1/dashboard/?token=<JWT>
← { "type": "replay", "count": 5, "events": [...] }
```

### Reconnect

```
→ ws://host/ws/provider/v1/dashboard/?token=<JWT>&last_event_id=123
← { "type": "replay", "count": 3, "events": [...] }
```

### Events (server → client)

```json
{
    "event_id": 456,
    "event_type": "task_updated",
    "entity_type": "provider_task",
    "entity_id": "42",
    "version": 3,
    "timestamp": "2026-05-11T12:00:00+00:00",
    "payload": {
        "task_id": 42,
        "title": "Water plant #3",
        "status": "in_progress",
        "priority": "urgent"
    }
}
```

### Client Messages

| Type | Purpose |
|------|---------|
| `ping` | Heartbeat → server responds `pong` |
| `replay` | Request missed events with `after_event_id` |
| `subscribe` | Future: subscription management |

## Replay / Resume Flow

```
Client disconnects → reconnects with last_event_id
  │
  ├── RealtimeEvent.objects.filter(created_at > last_event.created_at)
  │     ├── Events found? → replay (max 500, 24h window)
  │     └── Too many events? → fallback_required: true
  │
  └── Client sees fallback_required → uses REST API for full refresh
```

## Delta Polling Fallback

`GET /api/provider/v1/dashboard/delta/?since=<iso_datetime>&limit=20`

Returns changed tasks and recent realtime events since a timestamp.
Used by clients that cannot maintain a persistent WebSocket connection.

## Live Events

| Event | Source | Trigger |
|-------|--------|---------|
| `task_created` | Task service | `create_task()` |
| `task_updated` | Task service | `assign_task()`, `start_task()`, `complete_task()`, `cancel_task()` |
| `sla_breached` | SLA service | `evaluate_task_sla()` → breach |
| `task_escalated` | SLA service | `escalate_task()`, `upgrade_task_priority()` |
| `notification_created` | Notification pipeline | `enqueue_alert_notification()` |

## WebSocket Security

| Rule | Enforcement |
|------|-------------|
| No anonymous connections | JWT required in query string |
| No cross-tenant access | Connection joins `tenant_{schema}` group |
| Stale token rejected | JWT validation on connect |
| Revoked session rejected | Future: `MobileSession.is_active` check |

## Observability Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `realtime_connections_active` | Gauge | Current active WS connections |
| `realtime_events_total` | Counter | Total events published |
| `websocket_errors_total` | Counter | WS connection/auth errors |
| `replay_requests_total` | Counter | Replay requests |
| `delta_fallback_requests_total` | Counter | Delta polling requests |

## Event Store

`RealtimeEvent` table stores events for 24 hours (configurable).  Used for:

- WebSocket reconnect replay
- Delta polling fallback
- Mobile client catch-up after offline period

## Delta Sync Strategy

Mobile clients should:
1. Connect via WebSocket for live updates
2. On disconnect → reconnect with `last_event_id`
3. If replay count == limit → use `GET /dashboard/delta/` for full refresh
4. Fall back to polling `GET /dashboard/delta/` if WebSocket unavailable

## Files

| File | Purpose |
|------|---------|
| `identity/models/mobile_session.py` | Mobile session with JWT tracking |
| `provider_ops/models/realtime_event.py` | Event store for replay |
| `provider_ops/services/realtime_event_service.py` | Publish, broadcast, replay |
| `provider_ops/realtime/consumers.py` | WebSocket consumer |
| `provider_ops/realtime/routing.py` | WebSocket URL patterns |
| `provider_ops/api/views/replay.py` | Replay REST endpoint |
| `provider_ops/api/views/delta.py` | Delta polling fallback |
| `config/asgi.py` | Channels-enabled ASGI app |
