# B2B Key Lifecycle

Phase 7 moves B2B HMAC credentials from connection-level placeholders into explicit `ProviderKey` records.

## Ownership

`ProviderConnection` and `ProviderKey` live in the owner tenant schema. The owner remains the canonical source of truth and controls which provider tenant can receive synchronized data.

Provider tenants do not read owner schemas directly. Provider inbound authentication currently uses a test/settings key lookup path until cross-tenant key discovery is designed.

## ProviderKey

`ProviderKey` stores metadata only:

- `provider_connection`
- `key_id`
- `secret_reference`
- `status`: `active`, `disabled`, `revoked`, `rotated`
- `valid_from`
- `valid_until`
- `created_at`
- `rotated_at`
- `revoked_at`

It never stores a plain shared secret.

## Secret Resolver

Outbound delivery resolves `ProviderKey.secret_reference` through a resolver:

- `SettingsSecretResolver` for local/test settings
- `InMemorySecretResolver` for unit tests
- later: Vault, KMS, or cloud secret manager

The HMAC signing path receives only the resolved secret value in memory. Secrets are not logged and are not stored in the public schema.

## Lifecycle Rules

- A provider connection may have only one `active` key.
- Active keys must be within their validity window.
- Revoked, disabled, rotated, or expired keys cannot sign requests.
- Rotation marks the old key as `rotated`, sets `valid_until`, and creates a new `active` key.
- Revoke marks the key as `revoked`, sets `valid_until`, and prevents future signing.

## Audit

Key lifecycle services emit integration audit events:

- `key_created`
- `key_rotated`
- `key_revoked`

Audit writes are best-effort and must not break the primary key lifecycle transaction. Audit metadata must not include plain secrets.
