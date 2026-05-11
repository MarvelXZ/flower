# Realtime Sync Strategy

## WebSocket Protocol

**Connect**: `ws://host/ws/provider/v1/dashboard/?token=<JWT>&last_event_id=<id>`

**Reconnect** (exponential backoff): 1s → 2s → 4s → 8s → 16s → 32s → 60s (max)

**Heartbeat**: Client sends `{"type": "ping"}` every 30s → server responds `{"type": "pong"}`

## Event Flow

```
Backend event (task_created)
  │
  ├── RealtimeEvent store (DB)  ← always persisted
  │
  ├── Channels broadcast → WebSocket client
  │     ├── Client receives → update Riverpod state
  │     └── Client persists → local Drift DB
  │
  └── REST replay fallback (GET /provider/v1/realtime/replay/)
        └── After disconnect, before WebSocket reconnect
```

## Replay Strategy

| Scenario | Action |
|----------|--------|
| Fresh login | `?last_event_id=0` → full replay (max 500 events, 24h) |
| Short disconnect | `?last_event_id=<id>` → missed events only |
| Long disconnect | Replay hits limit → `fallback_required: true` → delta sync |
| WS unavailable | Polling `GET /dashboard/delta/` |

## Mobile App Sync Flow

```dart
Future<void> syncOnStartup() async {
  // 1. Replay missed realtime events
  final replayEvents = await replayService.fetch(afterEventId: _cursor);
  if (replayEvents.fallbackRequired) {
    // 2. Delta sync if replay insufficient
    final delta = await deltaSyncService.fetchDelta();
    _localDb.upsertTasks(delta.tasks);
  } else {
    _localDb.applyEvents(replayEvents.events);
  }
  // 3. Connect WebSocket for live updates
  await wsClient.connect();
}
```
