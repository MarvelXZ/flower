# Engagement Lifecycle

`ProviderEngagement` represents a bilateral agreement between an owner tenant
and a provider tenant.  It lives in the **public/owner** schema so that the
owner is the canonical source of truth for the relationship.

## Model

`ProviderEngagement` lives in `apps.integrations.models.engagement`.

| Field               | Purpose                                          |
|---------------------|--------------------------------------------------|
| `owner_tenant_id`   | The owner tenant side of the engagement           |
| `provider_tenant_id`| The provider tenant side of the engagement        |
| `status`            | `pending` / `active` / `suspended` / `revoked`   |
| `scopes`            | Allowed sync scopes                               |
| `created_at`        | Creation timestamp                                |
| `activated_at`      | When the engagement became active                 |
| `suspended_at`      | When the engagement was suspended                 |
| `revoked_at`        | When the engagement was revoked (terminal)        |

There is at most one engagement per `(owner_tenant_id, provider_tenant_id)`
pair (enforced by a unique constraint).

## Status Transitions

```
                ┌──────────┐
                │  PENDING │
                └────┬─────┘
                    ╱ ╲
                   ╱   ╲
                  ▼     ▼
            ┌────────┐  ┌──────────┐
            │ ACTIVE │  │ REVOKED  │ (terminal)
            └──┬──┬──┘  └──────────┘
               │  ╲
               │   ╲
               ▼    ▼
        ┌───────────┐  ┌──────────┐
        │ SUSPENDED │  │ REVOKED  │ (terminal)
        └─────┬─────┘  └──────────┘
              │
              ├────────────┐
              ▼            ▼
        ┌──────────┐  ┌──────────┐
        │ ACTIVE   │  │ REVOKED  │ (terminal)
        └──────────┘  └──────────┘
```

Valid transitions:

| From         | To                       |
|--------------|--------------------------|
| `pending`    | `active`, `revoked`      |
| `active`     | `suspended`, `revoked`   |
| `suspended`  | `active`, `revoked`      |
| `revoked`    | *(none — terminal)*      |

## Sync Gating

Only an **active** engagement allows data synchronisation:

- **Owner → Provider (outbound):** The outbox delivery worker should check
  `get_active_engagement()` before forwarding events to a provider tenant.
- **Provider → Owner (inbound):** The provider inbound B2B API currently
  relies on the inbound key registry for authentication.  Engagement gating
  on the inbound side is reserved for a future phase.

## Service

All write operations go through `apps.integrations.services.engagement_service`:

- `create_engagement(...)` — creates a `pending` engagement
- `activate_engagement(...)` — activates a pending or suspended engagement
- `suspend_engagement(...)` — suspends an active engagement
- `revoke_engagement(...)` — revokes any engagement (terminal)
- `get_active_engagement(...)` — returns the active engagement for a pair

Invalid transitions raise `InvalidEngagementTransition`.

## Relationship to ProviderConnection

`ProviderConnection` is the older, owner-side model that stores delivery
metadata (base URL, API key placeholder, etc.).  `ProviderEngagement`
complements it by providing a lifecycle-managed agreement status that
`ProviderConnection` lacks.  A future phase may merge or align the two.

Phase 9A introduces the sync checkpoint foundation that gates on engagement
status.  See [Sync Checkpoints](SYNC_CHECKPOINTS.md).

- `assert_engagement_allows_sync()` raises `EngagementSyncNotAllowed` for
  non-`active` engagements.
- `start_sync_run()` refuses to create a run unless the engagement is
  `active`.
