# Flower

Flower is an enterprise multi-tenant SaaS platform for plant care, IoT monitoring, provider maintenance, marketplace workflows, and future mobile applications.

The backend is a Django modular monolith using django-tenants. Owner tenants are the canonical source of truth. Provider tenants receive data only through B2B APIs and outbox-driven synchronization.

## Backend

```bash
cd backend
uv sync
python manage.py check
pytest
```

## Docker

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Django backend: http://localhost:8000
- Django admin: http://localhost:8000/admin/
- API schema: http://localhost:8000/api/schema/
- PostgreSQL/PostGIS: localhost:5432
- Redis: localhost:6379
- MQTT: localhost:1883

## Project Layout

```text
backend/
  apps/
    tenancy/
    identity/
    locations/
    plants/
    pots/
    devices/
    telemetry/
    care_engine/
    integrations/
    provider_ops/
    marketplace/
    notifications/
    billing/
    audit/
docs/
infra/
docker-compose.yml
```

See [docs/INDEX.md](docs/INDEX.md).
