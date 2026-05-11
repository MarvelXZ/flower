# Provider Inbound Key Registry

Phase 8 replaces the settings-backed HMAC key lookup on the provider inbound
side with a tenant-safe registry model: `ProviderInboundKey`.

## Motivation

Earlier phases used `get_settings_key_by_key_id()` — a single test key
configured via Django settings — for provider inbound HMAC validation.  This
did not scale to multiple owner tenants per provider and did not enforce
source-owner binding.

The inbound key registry solves this by storing key metadata **in the provider
tenant schema**, where the provider tenant can manage keys for each owner
tenant it receives data from.

## Model

`ProviderInboundKey` lives in `apps.provider_ops.models.inbound_key` and is
therefore tenant-scoped to each provider tenant schema.

| Field                 | Purpose                                                   |
|-----------------------|-----------------------------------------------------------|
| `key_id`              | Public identifier sent in the `X-B2B-Key-Id` header       |
| `source_owner_tenant_id` | The owner tenant that this key authenticates            |
| `secret_reference`    | Resolver reference — never stores the plain secret        |
| `status`              | `active` / `disabled` / `revoked`                        |
| `valid_from`          | Start of validity window                                   |
| `valid_until`         | Optional end of validity window                            |
| `scopes`              | JSON list of allowed endpoint scopes                      |
| `created_at`          | Creation timestamp                                         |
| `revoked_at`          | Revocation timestamp                                       |

The `key_id` must be **unique** within the provider tenant schema.

## Source Owner Binding

Each `ProviderInboundKey` is bound to exactly one `source_owner_tenant_id`.
When the HMAC-authenticated request passes validation, the authentication
layer attaches `source_owner_tenant_id` to the Django request object as
`request.b2b_source_owner_tenant_id`.

Downstream views **must not trust** the `source_owner_owner_tenant_id` in the
request payload without cross-checking it against this auth context.  The
`validate_source_owner_id()` function enforces this:

- If auth context is present (HMAC path): payload value must match the key's
  binding, otherwise `SourceOwnerMismatchError` is raised.
- If auth context is absent (test API key path): payload value is used as-is.

## Scope Validation

The authentication layer maps request path prefixes to required scopes:

| Path prefix                        | Required scope       |
|------------------------------------|----------------------|
| `/api/b2b/v1/locations/`           | `locations:write`    |
| `/api/b2b/v1/devices/`             | `devices:write`      |
| `/api/b2b/v1/telemetry/`           | `telemetry:write`    |

If the `ProviderInboundKey.scopes` list does not contain the required scope,
the request is rejected with a 401 before it reaches the view.

## Settings Fallback

The old settings-backed lookup (`get_settings_inbound_key()`) is retained for
test/dev convenience but guarded by `settings.B2B_USE_SETTINGS_KEY`.  When
`B2B_USE_SETTINGS_KEY` is `False` (the default), only the database registry
is consulted.

## HMAC Authentication Flow

```
Request → X-B2B-Key-Id
         ↓
Lookup ProviderInboundKey in provider tenant schema
   (fall back to settings if B2B_USE_SETTINGS_KEY=True)
         ↓
Check status == active + within validity window
         ↓
Resolve shared secret via secret_reference
         ↓
Verify HMAC-SHA256 signature
         ↓
Validate scope for endpoint
         ↓
Attach source_owner_tenant_id to request
         ↓
View processes request
```
