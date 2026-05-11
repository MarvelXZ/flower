# Sync Orchestration & Scheduling

Phase 10 adds the production-grade orchestration layer on top of the sync
engine.  This layer provides:

- Management command for operator-driven sync
- Celery task orchestration for automated sync
- Periodic delta sync scheduling
- Stuck sync recovery
- Sync locking protection
- Sync health monitoring
- Sync audit events
- Metrics abstraction

## Architecture

```
CLI (manage.py sync_provider)
  │
  ├── acquire_sync_lock()     ← ensures at most one running sync per engagement
  ├── run_full_sync() / run_delta_sync() / run_resync()
  │     └── sync_engine_sync_service.py  ← existing Phase 9B engine
  ├── audit_sync_started/completed/failed()
  └── increment_metric()      ← Prometheus-ready counters

Celery Beat (every 15 min)
  │
  └── run_periodic_delta_syncs()
        ├── for each active engagement:
        │     ├── has_running_sync()? → skip
        │     └── run_delta_sync_task.delay()
        └── recover_stuck_sync_runs()
              └── marks stuck running runs as failed
```

## Locking Strategy

Uses a two-level approach:

1. **Query guard** — `has_running_sync()` checks if any `SyncRun` exists
   with `status in {pending, running}` for the engagement.
2. **Transaction-safe lock** — `acquire_sync_lock()` uses
   `select_for_update()` on the `ProviderEngagement` row inside a
   `transaction.atomic()` block, then re-checks for active runs.

This ensures:
- At most one running sync per engagement
- Transaction safety (lock released on commit/rollback)
- No deadlocks from concurrent Celery workers

```python
with transaction.atomic():
    ProviderEngagement.objects.select_for_update().get(pk=engagement.pk)
    if active_run_exists():
        raise SyncLockError(...)
```

## Management Command

```bash
python manage.py sync_provider --engagement=1 --mode=full
python manage.py sync_provider --engagement=1 --mode=delta
python manage.py sync_provider --engagement=1 --mode=resync --stream=locations
python manage.py sync_provider --engagement=1 --mode=full --dry-run
python manage.py sync_provider --engagement=1 --mode=delta --verbose
```

Dry-run mode shows:
- Engagement status
- Current sync health
- Whether sync would be accepted/rejected
- No events are actually delivered

## Celery Tasks

| Task | Purpose |
|------|---------|
| `run_delta_sync_task(engagement_id)` | Single delta sync |
| `run_full_sync_task(engagement_id)` | Single full sync |
| `run_resync_task(engagement_id, stream_name)` | Single stream resync |
| `run_periodic_delta_syncs()` | Delta sync for all active engagements |
| `recover_stuck_sync_runs()` | Recover stuck running runs |

## Periodic Delta Sync

`run_periodic_delta_syncs()` is designed to run on a Celery Beat schedule
(e.g. every 15 minutes):

1. Query all active engagements
2. For each engagement: skip if `has_running_sync()` → True
3. Dispatch `run_delta_sync_task.delay()` for the rest
4. Also runs `recover_stuck_sync_runs()` to clean up orphans

## Stuck Sync Recovery

`recover_stuck_sync_runs()` identifies sync runs where:

```python
status == running AND started_at < now - SYNC_RUN_TIMEOUT_SECONDS (1800s)
```

For each stuck run:
1. Sets `status = failed`, `failed_at = now`, `error = "sync_run_timeout"`
2. Records an `audit_sync_recovered` event

This prevents orphaned `running` state from blocking future syncs.

## Sync Health Monitoring

`integrations/services/sync_health_service.py` provides:

- **`get_sync_health_summary()`** — global aggregate across all engagements:
  - total_engagements / active_engagements
  - running_sync_count / failed_sync_count_24h
  - stuck_sync_count / dead_letter_count / retry_count

- **`get_engagement_sync_health(engagement)`** — per-engagement detail:
  - last_successful_sync / last_failed_sync
  - running_sync_count / failed_sync_count
  - checkpoint_age_seconds
  - retry_queue_size / dead_letter_count
  - overall_healthy boolean

- **`detect_unhealthy_engagements()`** — returns list of unhealthy engagements

- **Metrics counters:**
  - `runs_total`, `runs_failed_total`, `stuck_total`
  - `delta_runs_total`, `full_runs_total`
  - `duration_seconds` (running average)

## Audit Events

All audit events use the existing `AuditLog` model with `action=SYNC`:

| Event | Trigger |
|-------|---------|
| `sync_started` | When a Celery task starts a sync run |
| `sync_completed` | When a sync run completes successfully |
| `sync_failed` | When a sync run fails |
| `sync_cancelled` | When a sync run is cancelled |
| `sync_recovered` | When a stuck run is recovered |

Audit writes are best-effort and must not break the primary flow.

## Engagement Gating

- **`acquire_sync_lock()`** calls `ProviderEngagement.objects.select_for_update()`
  and checks for active runs — only `active` engagements pass.
- **Celery tasks** call `acquire_sync_lock()` before running.
- **Management command** calls `acquire_sync_lock()` before executing.
- **Periodic sync** skips engagements that already have a running sync.

## Files

| File | Purpose |
|------|---------|
| `integrations/services/sync_locking.py` | Sync lock acquire/release |
| `integrations/services/sync_health_service.py` | Health monitoring + metrics |
| `integrations/services/sync_audit.py` | Best-effort audit events |
| `integrations/tasks/sync_tasks.py` | Celery task definitions |
| `integrations/management/commands/sync_provider.py` | CLI command |
