# Sync Checkpoints

Phase 9A adds the foundation for tracking synchronisation progress between
owner and provider tenants.  Phase 9B implements the full sync engine on
top of these primitives — see [Sync Engine](SYNC_ENGINE.md).

## Models

### SyncRun

Tracks a single synchronisation run.  Each run belongs to exactly one
`ProviderEngagement` and has a `run_type` that describes the scope.

| Field        | Purpose                                          |
|--------------|--------------------------------------------------|
| `engagement` | FK to `ProviderEngagement`                       |
| `run_type`   | `full` / `delta` / `resync`                      |
| `status`     | `pending` / `running` / `completed` / `failed` / `cancelled` |
| `started_at` | When the run started                             |
| `completed_at` | When the run completed                         |
| `failed_at`  | When the run failed                              |
| `error`      | Error detail (set when failed/cancelled)         |
| `stats`      | JSON blob for aggregated counts                  |

### SyncCheckpoint

Records the last-known-event for a data stream within an engagement.  The
checkpoint allows the sync engine to resume from where it left off rather
than replaying the full history.

| Field                 | Purpose                                        |
|-----------------------|------------------------------------------------|
| `engagement`          | FK to `ProviderEngagement`                     |
| `stream_name`         | Logical stream name (e.g. `locations`, `devices`, `telemetry`) |
| `last_event_id`       | Outbox event UUID of the last synced event     |
| `last_event_created_at` | Timestamp of the last synced event            |
| `last_successful_run` | FK to the last `SyncRun` that updated this checkpoint |
| `updated_at`          | Auto-updated timestamp                         |

There is at most one checkpoint per `(engagement, stream_name)` pair.

### SyncItem

An individual event within a sync run.  Each item corresponds to one outbox
event that the sync engine attempted to process.

| Field           | Purpose                                     |
|-----------------|---------------------------------------------|
| `sync_run`      | FK to `SyncRun`                             |
| `event_id`      | Outbox event UUID                           |
| `event_type`    | Event type (e.g. `location.created`)        |
| `aggregate_type`| Aggregate type (e.g. `Location`, `Device`)  |
| `aggregate_id`  | Aggregate identifier                        |
| `status`        | `pending` / `processed` / `failed` / `skipped` |
| `error`         | Error detail when processing failed         |
| `created_at`    | When the item was created                   |
| `processed_at`  | When the item was processed                 |

## Terminal Statuses

### SyncRun

| Status       | Terminal? | Can transition to                             |
|--------------|-----------|-----------------------------------------------|
| `pending`    | No        | `running`, `cancelled`                        |
| `running`    | No        | `completed`, `failed`, `cancelled`            |
| `completed`  | **Yes**   | *(none)*                                      |
| `failed`     | **Yes**   | *(none)*                                      |
| `cancelled`  | **Yes**   | *(none)*                                      |

Once a sync run reaches a terminal status it can never transition again.

### Engagement

| Status      | Allows sync? |
|-------------|-------------|
| `pending`   | ❌          |
| `active`    | ✅          |
| `suspended` | ❌          |
| `revoked`   | ❌ (terminal) |

## Checkpoint Idempotency

`update_checkpoint()` is idempotent:

- If no checkpoint exists for the stream, one is created.
- If a checkpoint already exists and the new event timestamp is **strictly
  newer**, the checkpoint is advanced.
- If the new event timestamp is **the same or older**, the checkpoint is
  **not** modified.  This prevents out-of-order delivery from rewinding
  progress.

## Service Layer

All write operations go through `apps.integrations.services.sync_service`:

- `start_sync_run(engagement, run_type)` — creates a `pending` run (requires
  `active` engagement)
- `complete_sync_run(sync_run, stats)` — marks a running run as `completed`
- `fail_sync_run(sync_run, error)` — marks a running run as `failed`
- `cancel_sync_run(sync_run, reason)` — cancels a pending/running run
- `record_sync_item(sync_run, event, status)` — records a sync item
- `update_checkpoint(engagement, stream_name, event)` — advances checkpoint
- `get_checkpoint(engagement, stream_name)` — reads current checkpoint

## What This Unlocks

With these primitives in place, the future sync engine can:

1. Look up `get_active_engagement()` to verify sync is allowed.
2. Call `start_sync_run()` to begin a cycle.
3. Query the outbox from the last checkpoint via `get_checkpoint()`.
4. Process each event — calling `record_sync_item()` — then advance the
   checkpoint.
5. Call `complete_sync_run()` or `fail_sync_run()` when done.
