# Offline-First Sync Strategy

## Data Flow

```
App Startup
  │
  ├── Check auth token (secure storage)
  │     ├── No token → LoginScreen
  │     └── Token exists →
  │           ├── WebSocket connect + replay (last_event_id)
  │           ├── Delta sync fallback (GET /dashboard/delta/)
  │           └── Render task list from local DB
  │
  Online (WebSocket connected)
  │
  ├── Receive realtime events
  │     ├── Update in-memory state (Riverpod)
  │     └── Persist to local DB (Drift)
  │
  User action (assign, complete, etc.)
  │
  ├── Optimistic UI update
  ├── Send API request
  │     ├── Success → confirm local change
  │     └── Failure → rollback + show error
  │
  Offline (no WebSocket)
  │
  ├── Read from local DB
  ├── Queue pending actions
  └── On reconnect: replay + delta sync → apply pending
```

## Sync Priority

1. **Realtime events** (WebSocket) — instant, acceleration layer
2. **Replay** (WS `replay` message) — catch up after reconnect
3. **Delta sync** (REST `GET /dashboard/delta/`) — fallback when WS unavailable
4. **Full refresh** (REST `GET /tasks/`) — manual pull-to-refresh

## Conflict Resolution

| Scenario | Strategy |
|----------|----------|
| Client task updated offline | Use server version (backend is canonical) |
| Task assigned by another worker | Accept server state, notify user |
| Stale version (409 Conflict) | Re-fetch from server, apply latest |
| Pending action conflicts | Discard pending, re-apply if still valid |

## Local Database

- Drift SQLite for offline cache
- Tables: `tasks`, `sla`, `sync_metadata`, `pending_actions`
- `sync_metadata` stores last known event ID + sync timestamp
- Never the canonical source — only a cache
