# Owner Canonical Sync Engine

Phase 9B implements the full synchronisation engine that replays owner
outbox events to a provider tenant through the existing delivery pipeline.

## Sync Strategies

| Strategy  | Use case                        | Behaviour                                            |
|-----------|---------------------------------|------------------------------------------------------|
| **Full**  | Initial provider onboarding     | Replays every outbox event from the beginning        |
| **Delta** | Recovery after short downtime   | Resumes from the last checkpoint                     |
| **Resync**| Stream-specific correction      | Clears one stream's checkpoint then does full sync   |

## Entry Points

All exposed through `apps.integrations.services.sync_engine_service`.

Higher-level orchestration with locking, scheduling, health monitoring, and
audit events is documented in [Sync Orchestration](SYNC_ORCHESTRATION.md).

Phase 11 adds the rule & alert engine — see [Rule & Alert Engine](RULE_ALERT_ENGINE.md).

- **`run_full_sync(engagement)`** — starts a full sync run, processes all
  streams from the beginning, completes the run.
- **`run_delta_sync(engagement)`** — starts a delta sync run, processes
  only streams with events newer than the checkpoint, completes the run.
- **`run_resync(engagement, stream_name)`** — deletes the checkpoint for
  the given stream, then runs a full resync of all streams.

## Execution Flow

```
run_full_sync / run_delta_sync / run_resync
  │
  ├── start_sync_run()       → engagement gating (must be active)
  ├── _execute_sync_run()
  │     ├── _transition_to_running()
  │     ├── _resolve_streams()    → [(stream, aggregate_type), …]
  │     ├── for each stream:
  │     │     ├── get_checkpoint()
  │     │     ├── _process_stream()
  │     │     │     ├── query outbox events (filtered by aggregate_type)
  │     │     │     ├── for each event:
  │     │     │     │     └── _deliver_and_record()
  │     │     │     │           ├── deliver_outbox_event(event)
  │     │     │     │           ├── on success → _record_processed_item()
  │     │     │     │           └── on failure → _record_failed_item()
  │     │     │     └── update_checkpoint() with last successful event
  │     │
  │     └── complete_sync_run() with stats
  │
  └── on SyncNotAllowed → cancel_sync_run()
      on Exception      → fail_sync_run()
```

## Stream Mapping

| `aggregate_type` | `stream_name` | Outbox event examples              |
|------------------|---------------|------------------------------------|
| `Location`       | `locations`   | `location.created`, `location.updated` |
| `Device`         | `devices`     | `device.created`, `device.updated` |
| `SensorReading`  | `telemetry`   | `SensorReadingReceived`            |

## Engagement Gating

All public entry points (`run_full_sync`, `run_delta_sync`, `run_resync`)
call `start_sync_run()` which in turn calls `assert_engagement_allows_sync()`.
If the engagement is not `active`, `SyncNotAllowed` is raised and the run is
cancelled.

## Delivery Reuse

The engine delegates HTTP delivery to the existing `deliver_outbox_event()`
pipeline.  This means HMAC signing, transport selection, retry logic, and
dead-letter handling are all reused without duplication.

## Checkpoint Behaviour

- After processing each stream, the checkpoint is advanced to the **last
  successfully delivered event** in that stream.
- If a single event fails (SyncEngineEventError), the engine continues to
  the next event.  The checkpoint is only advanced to the last *successful*
  event.
- Full and resync modes ignore existing checkpoints — they start from the
  beginning.
- Delta mode queries events *after* the checkpoint timestamp.

## Terminal States

SyncRun terminal states (`completed`, `failed`, `cancelled`) are enforced
by `sync_service` — once terminal, a run can never transition again.
