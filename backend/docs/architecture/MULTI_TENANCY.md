# Multi-Tenancy Architecture

PlantOps uses **django-tenants** with PostgreSQL schemas for physical tenant isolation.

## Schema Layout

| Schema | Purpose |
|---|---|
| `public` | Shared tables: `tenants_client`, `tenants_domain`, Django migrations |
| `<tenant_schema>` | Isolated tables for each tenant (e.g., `demo`, `acme`) |

## Tenant Routing

1. Incoming request hits Nginx.
2. Nginx forwards to Django.
3. `TenantMainMiddleware` inspects the `Host` header.
4. Middleware looks up the domain in `tenants_domain`.
5. If found, the connection is switched to the tenant's schema.
6. If not found, a 404 is returned.

## Fail-Closed Isolation

- **Default behavior**: If no tenant is resolved, the request is rejected.
- **Public schema**: Only accessible for the `tenants` app and Django admin.
- **Cross-tenant queries**: Explicitly prohibited. Use `tenant_context()` only in background jobs.
- **No schema hopping in views**: Views must never call `set_schema()` or similar directly.

## SHARED_APPS vs TENANT_APPS

### SHARED_APPS
These apps live in the `public` schema:
- `django_tenants`
- `django.contrib.*` (core)
- `rest_framework`, `drf_spectacular`
- `apps.tenancy`

### TENANT_APPS
These apps are replicated in every tenant schema:
- All bounded contexts (`identity`, `locations`, `plants`, `pots`, `devices`, `telemetry`, `care_engine`, `integrations`, `provider_ops`, `notifications`, `billing`, `audit`)

## Creating a Tenant

```python
from apps.tenancy.services import create_tenant

tenant = create_tenant(
    name="Acme Corp",
    slug="acme",
    kind=TenantKind.OWNER,
)
```

## Migrations

Always run migrations for both shared and tenant schemas:

```bash
python manage.py migrate_schemas --shared
python manage.py migrate_schemas --tenant
```

## Background Jobs

Celery tasks that touch tenant data must explicitly enter the tenant context:

```python
from django_tenants.utils import tenant_context
from apps.tenancy.models import Client

tenant = Client.objects.get(schema_name="acme")
with tenant_context(tenant):
    # Do tenant-specific work
    pass
```
