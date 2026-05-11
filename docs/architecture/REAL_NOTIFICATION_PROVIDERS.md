# Real Notification Providers

Phase 13 replaces the mock-only notification delivery with real provider
transports for push (FCM) and email (SMTP), while keeping the
``NotificationOutbox`` state machine and retry/dead-letter pipeline intact.

## Architecture

```
enqueue_alert_notification()
  │
  ├── resolve_channels(severity)       ← severity-based routing
  ├── check_preferences_allows()       ← NotificationPreference filtering
  └── for each allowed channel:
        └── NotificationOutbox.create(channel=push/email/in_app)
              │
              ▼
Worker → deliver_notification(notification)
  │
  ├── channel == "push"   → FCMNotificationTransport
  ├── channel == "email"  → EmailNotificationTransport
  └── default             → MockNotificationTransport (fallback)
```

## Routing

| Severity  | Default channels       |
|-----------|-----------------------|
| critical  | push + email          |
| warning   | push                  |
| info      | in_app                |

Routing is resolved by `routing_service.resolve_channels()` and can be
overridden by ``NotificationPreference`` per recipient.

## FCM Transport

``FCMNotificationTransport`` (`notifications/transports/fcm.py`)

| Aspect | Detail |
|--------|--------|
| SDK | `firebase-admin` (optional dependency) |
| Init | Service account JSON from `FCM_CREDENTIALS_FILE` |
| Delivery | `messaging.send_multicast()` to all active FCM tokens |
| Invalid tokens | UNREGISTERED/INVALID_ARGUMENT/NOT_FOUND → deactivate token |
| Retryable | Transport errors, all messages failed |
| Settings | `FCM_ENABLED`, `FCM_CREDENTIALS_FILE`, `FCM_DEFAULT_TTL_SECONDS` |

## SMTP Email Transport

``EmailNotificationTransport`` (`notifications/transports/email.py`)

| Aspect | Detail |
|--------|--------|
| Backend | Django `send_mail` using configured SMTP backend |
| Destinations | Active verified `EmailDestination` records |
| Retryable | SMTP timeout/connection error |
| Permanent | No active destinations |
| Settings | `EMAIL_ENABLED`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_TIMEOUT_SECONDS`, etc. |

## Retry / Permanent Classification

| Condition | Classification | Action |
|-----------|---------------|--------|
| Provider unavailable | Retryable | `mark_retry` with 60s backoff |
| Timeout | Retryable | `mark_retry` |
| 429 / 5xx | Retryable | `mark_retry` |
| Invalid push token | Permanent | `mark_dead_letter` + deactivate token |
| Invalid email | Permanent | `mark_dead_letter` |
| Unauthorized | Permanent | `mark_dead_letter` |
| Malformed payload | Permanent | `mark_dead_letter` |

## Preference Enforcement

``check_preferences_allows()`` is called during **enqueue**:

- If no preference exists → **allowed** (opt-out model)
- If preference exists and `enabled=False` → **blocked** (no NotificationOutbox created)
- If preference has higher `alert_severity_min` than alert severity → **blocked**

This means disabled preferences never create NotificationOutbox records,
avoiding unnecessary noise.

## DevicePushToken Model

Registered push tokens with unique token constraint. Invalid tokens are
**deactivated** (not deleted) during FCM delivery.

## EmailDestination Model

Verified email addresses per tenant. Only active AND verified destinations
receive notification emails.

## Security Rules

- Push tokens are not logged
- SMTP passwords are not logged
- Provider secrets are not logged
- Full email body is not logged unless explicitly needed for debugging
- Token deactivation is safe (does not cascade)

## Files

| File | Purpose |
|------|---------|
| `notifications/models/device_push_token.py` | Push token model |
| `notifications/models/email_destination.py` | Email destination model |
| `notifications/transports/fcm.py` | FCM push transport |
| `notifications/transports/email.py` | SMTP email transport |
| `notifications/services/routing_service.py` | Channel resolution + preference check |
| `notifications/services/notification_delivery_service.py` | Auto-resolves transport per channel |
| `notifications/tasks/notification_tasks.py` | Channel-specific Celery tasks |
