# Offline Operator UX

## User-visible states

| State | Indicator | UX Behavior |
|-------|-----------|-------------|
| **Online** | Green dot / none | Normal push-based realtime updates |
| **Syncing** | Spinner in app bar | Silent background sync |
| **Offline** | Persistent amber banner | "Working offline — changes will sync when connected" |
| **Stale data** | Faint warning on cards | "Last synced 30 min ago" |
| **Pending actions** | Badge count | "2 actions pending sync" |
| **Sync failed** | Red dismissible banner | "Sync failed — tap to retry" |
| **Conflict** | Conflict dialog | "This task was updated by another worker" |

## Pending Action Lifecycle

```
User action (assign, complete, etc.)
  │
  ├── Online: send API → success → confirm UI
  │                       → failure → show error
  │
  └── Offline: queue to PendingActions table
                ├── Show "pending" badge on card
                ├── On reconnect: replay → process queue
                └── On conflict: discard pending, refresh from server
```

## Offline First Read Strategy

```
Task list requested
  │
  ├── 1. Read from Drift SQLite (instant)
  ├── 2. Show cached data immediately
  ├── 3. Fetch from API in background
  │     ├── Success → update DB + UI
  │     └── Failure → keep showing cached data + stale indicator
  └── 4. WebSocket events → incremental updates
```
