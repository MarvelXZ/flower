# SLA & Escalation Engine

Phase 15 adds a production-grade SLA tracking and escalation layer on top
of the ``ProviderTask`` workflow.

## Architecture

```
Task lifecycle                  SLA layer                      Notification
─────────────────              ──────────                     ────────────

create_task() ──→ create_task_sla()        (response_due_at, resolution_due_at)
assign_task() ──→ mark_task_assigned()     (first_assigned_at)
complete_task() → mark_task_resolved()     (resolved_at)

Periodic evaluation
evaluate_open_task_slas() ──→ evaluate_task_sla(task)
  │
  ├── Unassigned past response_due_at
  │     └── response_sla_breach → escalate_task()
  │           ├── TaskEscalationEvent
  │           ├── escalation_level += 1
  │           └── enqueue notification
  │
  └── Not completed past resolution_due_at
        └── resolution_sla_breach → escalate_task()
              ├── priority NOT urgent → upgrade_task_priority()
              └── enqueue notification
```

## SLA Targets

| Priority | Response SLA | Resolution SLA |
|----------|-------------|----------------|
| LOW | 24 h | 72 h |
| NORMAL | 8 h | 24 h |
| HIGH | 2 h | 8 h |
| URGENT | 15 min | 2 h |

## Escalation Flow

```
1. Response SLA breach detected
   │
   ├── sla.breached_response_sla = True
   ├── TaskEscalationEvent(response_sla_breach)
   ├── escalation_level += 1
   ├── Notification: task_sla_breached
   │
   └── [Flag is permanent — never reset]

2. Resolution SLA breach detected
   │
   ├── sla.breached_resolution_sla = True
   ├── TaskEscalationEvent(resolution_sla_breach)
   ├── escalation_level += 1
   ├── IF priority != urgent → upgrade_task_priority()
   │     └── TaskEscalationEvent(priority_upgrade)
   ├── IF urgent overdue > threshold → escalation_level += 1
   │
   └── All escalation events create notifications
```

## Notification Integration

SLA breaches and escalations enqueue notifications through the existing
``NotificationOutbox`` pipeline:

| Event | Notification type |
|-------|-------------------|
| SLA breached | `task_sla_breached` |
| Priority upgraded | `task_priority_upgraded` |
| Task escalated | `task_escalated` |

The SLA service only enqueues — delivery is async via the worker.

## Priority Auto-Upgrade

| Current | Upgraded to |
|---------|-------------|
| LOW | NORMAL |
| NORMAL | HIGH |
| HIGH | URGENT |
| URGENT | (no-op — already highest) |

## Periodic Tasks

All run via Celery:

| Task | Schedule | Purpose |
|------|----------|---------|
| `evaluate_open_task_slas` | Every 5 min | Breach detection + escalation |
| `process_overdue_tasks` | Every 15 min | Overdue processing |
| `send_task_reminders` | Every 30 min | Placeholder reminders |

## Models

### TaskSLA

One-to-one with ``ProviderTask``:

| Field | Purpose |
|-------|---------|
| `response_due_at` | Deadline for first assignment |
| `resolution_due_at` | Deadline for completion |
| `first_assigned_at` | When the task was first assigned |
| `resolved_at` | When the task was completed |
| `breached_response_sla` | True if response SLA was missed |
| `breached_resolution_sla` | True if resolution SLA was missed |
| `escalation_level` | How many times this task was escalated |
| `last_escalated_at` | Last escalation timestamp |

### TaskEscalationEvent

Audit trail for each escalation action.

## Metrics

Placeholder counters (replace with Prometheus when ready):

- `flower_sla_breaches_total`
- `flower_task_escalations_total`
- `flower_overdue_tasks_total`
- `flower_sla_response_seconds`
- `flower_sla_resolution_seconds`

## Files

Phase 16 adds the mobile-ready dashboard API on top of this —
see [Mobile-ready API](MOBILE_READY_API.md).

| File | Purpose |
|------|---------|
| `provider_ops/domain/enums.py` | TaskEscalationType |
| `provider_ops/models/sla.py` | TaskSLA, TaskEscalationEvent |
| `provider_ops/services/sla_policy_service.py` | SLA target definitions |
| `provider_ops/services/sla_service.py` | Breach detection + escalation |
| `provider_ops/services/sla_metrics.py` | Metrics counters |
| `provider_ops/selectors/sla_selectors.py` | SLA read queries |
| `provider_ops/tasks/sla_tasks.py` | Periodic Celery tasks |
| `provider_ops/api/views/sla.py` | SLA dashboard API |
