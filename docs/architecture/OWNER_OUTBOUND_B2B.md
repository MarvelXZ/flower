# Owner Outbound B2B

Phase 6 connects the owner-side `IntegrationOutbox` pipeline to the provider inbound B2B contract through a replaceable transport. `HttpProviderTransport` is now available for real HTTP delivery, while `MockProviderTransport` remains for tests.

Owner tenants remain the canonical source of truth. `ProviderConnection` records live in the owner tenant schema because the owner controls which provider tenants are allowed to receive synchronized data.

## Flow

1. A worker claims `pending` or `retry` outbox events with `select_for_update(skip_locked=True)`.
2. The event moves to `processing` through `OutboxService`.
3. `deliver_outbox_event()` loads active `ProviderConnection` records for the event.
4. The delivery service loads the active `ProviderKey` for the connection.
5. `ProviderKey.secret_reference` is resolved through the secret resolver.
6. `map_outbox_event_to_provider_request()` maps the event into the provider inbound contract.
7. The request body is serialized deterministically and signed with HMAC.
8. A replaceable transport sends the request.
9. The delivery service records an `OutboxDelivery` attempt.
10. The event moves to `processed`, `retry`, or `dead_letter` through `OutboxService`.

No provider code reads owner schemas directly.

## ProviderConnection

`ProviderConnection` contains owner-tenant delivery metadata:

- `provider_tenant_id`
- `provider_base_url`
- legacy `api_key_hash`, `key_id`, and `shared_secret_reference` fields kept for compatibility
- `status`: `active`, `disabled`, `revoked`
- `scopes`
- `created_at`
- `updated_at`
- `revoked_at`

Revoked and disabled connections are ignored by delivery selection.

Signing no longer reads connection-level secret fields. New HMAC signing uses `ProviderKey`.

## ProviderKey

`ProviderKey` stores key metadata per connection:

- `key_id`
- `secret_reference`
- `status`
- validity window
- rotation/revoke timestamps

Only one key may be `active` for a connection. Rotated, revoked, disabled, or expired keys are not used for outbound signing.

## Event Mapping

`SensorReadingReceived` maps to:

```text
POST /api/b2b/v1/telemetry/batch/
```

Payload:

```json
{
  "schema_version": "1.0",
  "source_owner_tenant_id": "owner",
  "items": [
    {
      "external_reading_id": "reading-1",
      "external_device_id": "device-1",
      "measured_at": "2026-05-11T10:05:00Z",
      "soil_moisture": 42.5,
      "temperature": 23.1,
      "air_humidity": 55.0,
      "light_level": 300,
      "battery_level": 87
    }
  ]
}
```

The outbound idempotency key is derived from the owner outbox event idempotency key, so retries of the same event replay safely against provider inbound idempotency rules.

## Transports

Both transports implement `send(request)`:

- `HttpProviderTransport` sends signed POST JSON with a required timeout.
- `MockProviderTransport` stores requests in memory and returns configurable responses for tests.

The transport boundary keeps delivery logic testable and lets the network layer evolve without changing outbox state transitions.

## HMAC Headers

Outbound HTTP requests include `X-B2B-Timestamp`, `X-B2B-Key-Id`, `X-B2B-Signature`, and `X-Idempotency-Key`. `X-B2B-Key-Id` comes from the active `ProviderKey`. The signature is documented in [B2B Security](B2B_SECURITY.md).

## Failure Behavior

- Success response: `processing -> processed`
- Retryable transport failure or retryable response: `processing -> retry`
- Permanent response failure: `processing -> dead_letter`
- No active provider connection: `processing -> retry`
- Retryable failure at max retry count: `processing -> dead_letter`

Retryable responses are timeouts, connection failures, `429`, and `5xx`. Permanent responses include `400`, `401`, `403`, `404`, `409`, and `422`.
