# Tenant Bootstrap

Flower uses `apps.tenancy.Client` and `apps.tenancy.Domain` as the django-tenants models.

The local bootstrap command creates three development tenants:

- owner tenant: `owner` with domain `owner.localhost`
- provider tenant: `provider` with domain `provider.localhost`
- hybrid tenant: `hybrid` with domain `hybrid.localhost`

Run:

```bash
cd backend
uv run python manage.py migrate_schemas --shared
uv run python manage.py create_demo_tenants
uv run python manage.py migrate_schemas --tenant
```

The command is idempotent. Existing tenants are updated to the expected name, slug, kind, active state, and primary domain.

This command only prepares tenant bootstrap data. It does not create MQTT pipelines, provider B2B contracts, marketplace data, or business fixtures.
