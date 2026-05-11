# Integration Outbox

Flower uses an outbox because integration work must be recorded atomically with the owner data change that caused it. For telemetry, the owner `SensorReading`, `Device.last_seen_at`, and `IntegrationOutbox` event are written in one tenant transaction.

Phase 3 hardens the outbox as an internal delivery pipeline. Phase 6 adds owner outbound request mapping, HMAC signing, and a real HTTP transport behind the same replaceable transport interface. Phase 9A adds sync checkpoint models and services that will later drive outbox-based delta syncs from checkpoints.

## Event Envelope

Outbox records include:

- `event_id`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `payload`
- `status`
- `created_at`
- `available_at`
- `processed_at`
- `retry_count`
- `last_error`

`OutboxDelivery` records each internal processing attempt with `attempt_number`, `status`, `error`, and `created_at`.

## State Machine

Valid transitions:

- `pending -> processing`
- `retry -> processing`
- `processing -> processed`
- `processing -> retry`
- `processing -> dead_letter`

Invalid transitions fail closed through the outbox service layer. For example, `pending -> processed` is not allowed, and `processed -> retry` is not allowed.

`retry_count` increases only when an event moves to `retry` or `dead_letter`. `processed_at` is set only when an event moves to `processed`. `available_at` is moved forward when an event moves to `retry`.

## Claim Pattern

Workers call `claim_pending_events()`, which evaluates `get_pending_outbox_events()` inside a transaction. The selector filters only `pending` and `retry` events with `available_at <= now`, orders by `available_at` and `created_at`, and uses `select_for_update(skip_locked=True)`.

`skip_locked` lets multiple workers claim independent rows without blocking each other or double-processing the same event.

## Delivery

The Celery task claims events and calls `deliver_outbox_event()`. The delivery service maps outbox events to provider contract requests, signs requests, records delivery attempts, and moves the event through the state machine.

`HttpProviderTransport` sends deterministic signed JSON with a timeout. `MockProviderTransport` remains available for tests and local simulations.

Retryable failures are timeouts, connection errors, `429`, and `5xx`. Permanent failures include `400`, `401`, `403`, `404`, `409`, and `422`.
