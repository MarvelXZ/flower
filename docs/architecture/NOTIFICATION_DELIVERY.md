# Notification Delivery Foundation

Phase 12 adds the notification delivery pipeline that connects the Alert
lifecycle with an asynchronous outbox-based delivery mechanism, without
real FCM/APNs/email/SMS providers.

## Architecture

```
Alert lifecycle (alert_service)
  │
  ├── Alert created  → enqueue_alert_notification(ALERT_CREATED)
  └── Alert resolved → enqueue_alert_notification(ALERT_RESOLVED)
        │
        ▼
NotificationOutbox (pending)
        │
        ▼
Worker / Celery Task
  │
  ├── claim_pending_notifications()  ← select_for_update(skip_locked=True)
  ├── deliver_notification(notification, transport)
  │     ├── transport.send() → success       → mark_sent (terminal)
  │     ├── transport.send() → retryable     → mark_retry
  │     └── transport.send() → permanent     → mark_dead_letter (terminal)
  └── record_delivery_attempt()

Transport (replaceable):
  - MockNotificationTransport (testing)
  - future: FCM, APNs, email, SMS, webhook
```

## State Machine

```
                ┌──────────┐
                │ PENDING  │
                └────┬─────┘
                     │
              ┌──────▼──────┐
              │  RETRY      │
              └──────┬──────┘
                     │
              ┌──────▼──────┐
              │ PROCESSING   │
              └──┬───┬───┬──┘
                 │   │   │
    ┌────────────┘   │   └────────────┐
    ▼                ▼                ▼
┌──────┐       ┌────────┐      ┌────────────┐
│ SENT │       │ RETRY  │      │ DEAD_LETTER│ (terminal)
│(term)│       └────────┘      └────────────┘
└──────┘            │
                    └──→ PROCESSING (retry cycle)
```

## Models

### NotificationOutbox

| Field | Purpose |
|-------|---------|
| `event_id` | UUID — stable idempotency key |
| `notification_type` | `alert_created` / `alert_updated` / `alert_resolved` |
| `channel` | `push` / `email` / `sms` / `in_app` / `webhook` |
| `recipient_type` / `recipient_id` | Target routing |
| `alert` | FK to the source Alert |
| `payload` | JSON snapshot of the alert |
| `status` | `pending` → `processing` → `sent`/`retry`/`dead_letter` |

### NotificationDelivery

Records each delivery attempt (status, error, provider response).

### NotificationPreference

Per-recipient channel preference with `enabled` flag and `alert_severity_min` filter.

## Idempotency

- **`event_id`** is deterministic: `uuid.uuid5("notification:{type}:alert_{pk}")`
- Same `(alert_id, notification_type)` → same `event_id` → deduplicated
- Active (pending/processing/retry) records with the same `event_id` are returned instead of creating a duplicate

## Transport

Currently only `MockNotificationTransport` is implemented with three modes:
- `success` — always succeeds
- `retryable` — always returns a retryable error
- `permanent` — always returns a permanent failure

Phase 13 implements real push (FCM) and email (SMTP) transports —
see [Real Notification Providers](REAL_NOTIFICATION_PROVIDERS.md).

## Alert Service Integration

- `open_or_update_alert()` → enqueues `ALERT_CREATED` when creating a new alert
- `resolve_alert()` → enqueues `ALERT_RESOLVED`
- Alert updates (`last_seen_at` refresh) do **not** enqueue `ALERT_UPDATED` — documented decision to avoid notification storms

The alert service **only enqueues** — it never sends directly. Delivery is
always async via the outbox worker.

## Notification Preferences

`NotificationPreference` allows per-recipient filtering:
- `enabled=False` → notification should not be delivered on this channel
- `alert_severity_min` → only deliver alerts at this severity or higher
- Preference enforcement during enqueue is reserved for a future phase

## Files

| File | Purpose |
|------|---------|
| `notifications/models/noutbox.py` | NotificationOutbox, Delivery, Preference models |
| `notifications/domain/enums.py` | NotificationType, Channel, Status, RecipientType |
| `notifications/services/notification_outbox_service.py` | Outbox lifecycle service |
| `notifications/services/notification_delivery_service.py` | Delivery orchestration |
| `notifications/transports/base.py` | Transport protocol |
| `notifications/transports/mock.py` | Mock transport for testing |
| `notifications/tasks/notification_tasks.py` | Celery batch delivery task |
