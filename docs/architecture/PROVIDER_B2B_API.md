# Provider B2B API

Phase 4 adds the provider-side inbound REST contract for synchronized owner data. Phase 6 adds HMAC authentication support for real owner outbound HTTP delivery.

The API runs in the provider tenant schema. Provider code stores external copies of permitted owner data in `provider_ops` models and never reads the owner tenant schema directly.

## Base Path

```text
/api/b2b/v1/
```

## Authentication

Local/test requests may include:

```text
X-Provider-Api-Key: <key>
```

The key is compared with `B2B_TEST_API_KEY` from settings.

Signed owner outbound requests should include:

```text
X-B2B-Timestamp: <unix seconds>
X-B2B-Key-Id: <key identifier>
X-B2B-Signature: <hex hmac-sha256>
X-Idempotency-Key: <stable request key>
```

HMAC validation now uses a tenant-safe key registry — see
[Provider Inbound Key Registry](PROVIDER_INBOUND_KEY_REGISTRY.md).

The authentication flow:

1. Look up `ProviderInboundKey` by `X-B2B-Key-Id` in the provider tenant
   schema (with optional settings fallback when `B2B_USE_SETTINGS_KEY=True`).
2. Verify the key is `active` and within its validity window.
3. Resolve the shared secret via `secret_reference`.
4. Verify the HMAC-SHA256 signature.
5. Validate that the key's scopes allow the target endpoint.
6. Attach `source_owner_tenant_id` to the request for downstream views.

Unknown, revoked, disabled, or expired keys are rejected.  Keys without the
required scope for the endpoint are also rejected.

The old settings-backed lookup (`get_settings_key_by_key_id`) is replaced by
the registry.  A settings fallback exists only when
`B2B_USE_SETTINGS_KEY=True` (test/dev mode).

## Idempotency

Mutating endpoints require:

```text
X-Idempotency-Key: <unique request key>
```

Behavior:

- same key + same endpoint + same request hash returns the cached response
- same key + same endpoint + different request hash returns `409 Conflict`
- missing key returns `400 Bad Request`

Idempotency records are provider-tenant local.

## Endpoints

### Location Upsert

```text
POST /api/b2b/v1/locations/upsert/
```

Body:

```json
{
  "source_owner_tenant_id": "owner",
  "external_id": "loc-1",
  "name": "Office",
  "address": "Main street",
  "latitude": 44.8125,
  "longitude": 20.4612,
  "raw_payload": {}
}
```

Upserts `ExternalLocation` by `(source_owner_tenant_id, external_id)`.

The `source_owner_tenant_id` in the payload must match the key's binding when
HMAC authentication is used.  See [source owner binding](PROVIDER_INBOUND_KEY_REGISTRY.md#source-owner-binding).

### Device Upsert

```text
POST /api/b2b/v1/devices/upsert/
```

Body:

```json
{
  "source_owner_tenant_id": "owner",
  "external_id": "dev-1",
  "external_location_id": "loc-1",
  "name": "ESP32 Office",
  "status": "active",
  "raw_payload": {}
}
```

Upserts `ExternalDevice` by `(source_owner_tenant_id, external_id)`. Unknown `external_location_id` is rejected.

### Telemetry Batch

```text
POST /api/b2b/v1/telemetry/batch/
```

Body:

```json
{
  "schema_version": "1.0",
  "source_owner_tenant_id": "owner",
  "items": [
    {
      "external_device_id": "dev-1",
      "external_reading_id": "reading-1",
      "measured_at": "2026-05-11T10:05:00Z",
      "soil_moisture": 42.5,
      "temperature": 23.1,
      "air_humidity": 55.0,
      "light_level": 300,
      "battery_level": 87,
      "raw_payload": {}
    }
  ]
}
```

Creates or updates `TelemetryIngest` by `(source_owner_tenant_id, external_reading_id)`. Unknown `external_device_id` is rejected fail-closed.

### Sync Status

```text
GET /api/b2b/v1/sync/status/
```

Returns a lightweight authenticated health response for B2B clients.

## Not Implemented Yet

- full sync implementation gated on provider engagement status
- provider delivery worker integration
- encrypted secret resolution (currently resolver-based)
- marketplace, mobile, or billing behavior
