# B2B Security

Phase 6 adds HMAC signing for owner-to-provider B2B delivery while keeping the previous test API key path available for local tests. Phase 7 adds explicit provider key lifecycle and secret resolution.

## Required Headers

Signed B2B requests include:

```text
X-B2B-Timestamp: <unix seconds>
X-B2B-Key-Id: <key identifier>
X-B2B-Signature: <hex hmac-sha256>
X-Idempotency-Key: <stable outbox idempotency key>
```

Provider inbound endpoints still accept `X-Provider-Api-Key` in test mode. HMAC auth uses a key lookup path by `X-B2B-Key-Id`; today provider-side lookup is settings-backed for test/dev, and production should move to tenant-safe key discovery or OAuth2.

## Canonical String

The signature is `HMAC-SHA256` over:

```text
METHOD
PATH
TIMESTAMP
IDEMPOTENCY_KEY
SHA256_HEX_BODY
```

Bodies are serialized as deterministic JSON before signing and sending. This keeps the body hash stable across retries and makes tests deterministic.

## Timestamp Skew

Provider inbound HMAC verification rejects malformed or expired timestamps. The default tolerance is `B2B_HMAC_MAX_SKEW_SECONDS=300`.

## Secret Handling

`ProviderKey.secret_reference` points to the resolver entry for the active HMAC key. It is metadata, not the plain secret.

Available resolvers:

- `SettingsSecretResolver` for test/dev
- `InMemorySecretResolver` for unit tests
- later: Vault, KMS, or cloud secret manager

Logs must not contain API keys, shared secrets, full authorization headers, or sensitive payloads. Delivery logs may include event id, event type, provider tenant id, endpoint, status code, retry classification, and duration.

## Provider Inbound Key Registry (Phase 8)

Phase 8 replaces the settings-backed inbound key lookup with a tenant-safe
`ProviderInboundKey` model stored in the provider tenant schema.  Each key:

- Has a unique `key_id` within the provider tenant schema.
- Is bound to exactly one `source_owner_tenant_id`.
- Carries a `secret_reference` (never the plain secret).
- Has a status (`active` / `disabled` / `revoked`), validity window, and
  allowed endpoint scopes.

The HMAC authentication flow now:

1. Looks up the key by `X-B2B-Key-Id` in the provider tenant schema.
2. Verifies the key is active and within its validity window.
3. Resolves the shared secret via the `secret_reference`.
4. Verifies the HMAC-SHA256 signature.
5. Validates that the key's scopes allow the endpoint being called.
6. Attaches `source_owner_tenant_id` to the request as
   `request.b2b_source_owner_tenant_id`.

The old settings fallback is disabled by default (`B2B_USE_SETTINGS_KEY=False`).
Set it to `True` for local test mode only.

## Source Owner Binding

The payload `source_owner_tenant_id` must match the value bound to the
inbound key when HMAC authentication is used.  If they differ, the request
is rejected with a 401 before it reaches the view logic.  This prevents a
provider tenant from claiming data from an owner tenant they are not
authorised for.

When the legacy test API key path is used (no HMAC), the payload value is
trusted as-is — this is acceptable only in dev/test environments.

## Engagement Lifecycle (Phase 8)

Phase 8 introduces `ProviderEngagement` — a lifecycle-managed agreement
between an owner tenant and a provider tenant.  It lives in the public/owner
schema and has four statuses: `pending`, `active`, `suspended`, `revoked`.

Only an `active` engagement allows data synchronisation.  `revoked` is a
terminal state.

See [Engagement Lifecycle](ENGAGEMENT_LIFECYCLE.md) for the full status
transition diagram.

## Tenant Isolation

HMAC proves request origin for provider inbound APIs, but it does not change data ownership rules. Provider tenants still receive copied data through B2B endpoints and never read owner schemas directly.
