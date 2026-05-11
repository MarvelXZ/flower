# DDD Overview — Bounded Contexts

PlantOps is organized into **bounded contexts** (Django apps). Each context owns its own data, rules, and invariants. Cross-context communication happens through **domain events** or explicit **service calls** — never through direct foreign keys across contexts.

## Bounded Contexts

### 1. `tenants` (Shared Schema)
- **Responsibility**: Tenant provisioning, domain management, subscription linking.
- **Models**: `Client`, `Domain`
- **Notes**: Lives in the `public` schema. All other tenant data lives in isolated schemas.

### 2. `accounts` (Tenant Schema)
- **Responsibility**: Users, roles, permissions, authentication.
- **Models**: `UserProfile` (placeholder)
- **Notes**: Will extend or link to Django's `User`. Tenant-scoped.

### 3. `locations` (Tenant Schema)
- **Responsibility**: Physical locations (sites, greenhouses, indoor areas).
- **Models**: `Location` (placeholder)
- **Notes**: Locations group planters and devices.

### 4. `planters` (Tenant Schema)
- **Responsibility**: Planter (container) definitions and inventory.
- **Models**: `Planter` (placeholder)
- **Notes**: A planter holds one plant and one device at a time.

### 5. `plants` (Tenant Schema)
- **Responsibility**: Plant species, varieties, care profiles.
- **Models**: `PlantSpecies` (placeholder)
- **Notes**: Care profiles define thresholds for alerts.

### 6. `devices` (Tenant Schema)
- **Responsibility**: IoT device registry, firmware, connectivity.
- **Models**: `Device` (placeholder)
- **Notes**: Devices send raw readings. Devices NEVER write business state directly.

### 7. `measurements` (Tenant Schema)
- **Responsibility**: Raw sensor readings and processed snapshots.
- **Models**: `RawReading` (placeholder)
- **Notes**: **APPEND-ONLY**. Never update or delete. Time-series by nature.

### 8. `alerts` (Tenant Schema)
- **Responsibility**: Alert definitions, alert instances, thresholds.
- **Models**: `Alert` (placeholder)
- **Notes**: **APPEND-ONLY** events. An alert may spawn a task.

### 9. `tasks` (Tenant Schema)
- **Responsibility**: Tasks for gardeners/workers.
- **Models**: `Task` (placeholder)
- **Notes**: Tasks can be system-generated or manually created.

### 10. `notifications` (Tenant Schema)
- **Responsibility**: Notification channels, templates, delivery logs.
- **Models**: `NotificationLog` (placeholder)
- **Notes**: Supports email, SMS, push, in-app.

### 11. `billing` (Tenant Schema)
- **Responsibility**: Subscriptions, invoices, usage metering.
- **Models**: `Subscription` (placeholder)
- **Notes**: May integrate with Stripe or similar.

### 12. `audit` (Tenant Schema)
- **Responsibility**: Audit trails of manual actions.
- **Models**: `AuditLog` (placeholder)
- **Notes**: **APPEND-ONLY**. Every manual action by a user must be logged.

## DDD File Structure (per app)

```
apps/<context>/
  models.py      # Domain entities and value objects
  services.py    # Write operations ONLY
  selectors.py   # Read/query operations ONLY
  events.py      # Domain events (outbox pattern)
  admin.py       # Django admin configuration
  apps.py        # AppConfig
  tests/         # Unit tests
```

## Rules
- **No direct writes outside services.py.**
- **No direct reads outside selectors.py.**
- **No cross-context foreign keys.** Use IDs and events.
- **Models are placeholders for now.** Do not add fields until the domain is confirmed.
