# PlantOps / PlanterOps SaaS

Multi-tenant SaaS platform for IoT plant and planter management.

## Tech Stack

- **Backend**: Python 3.12+, Django 5.x, django-tenants, DRF, drf-spectacular, Celery, PostgreSQL 16, Redis, RabbitMQ
- **Frontend**: React 18, Vite, TypeScript, i18next
- **Operations**: Docker, Docker Compose, Nginx, Prometheus, Grafana
- **Package Manager**: uv (backend), npm (frontend)

## Quick Start (Docker)

1. Clone the repository and navigate to the project root.

2. Copy the environment file:
   ```bash
   cp .env.example .env
   ```

3. Start all services:
   ```bash
   docker compose up --build
   ```

4. Access the services:
   - Backend API: http://localhost:8000/api/
   - API Docs (Swagger): http://localhost:8000/api/docs/
   - API Schema: http://localhost:8000/api/schema/
   - Django Admin: http://localhost:8000/admin/
   - Frontend (Vite): http://localhost:5173/
   - RabbitMQ Management: http://localhost:15672/
   - Flower (Celery): http://localhost:5555/
   - PgAdmin: http://localhost:5050/

## Quick Start (Local Development)

### Backend

1. Install uv:
   ```bash
   pip install uv
   ```

2. Sync dependencies:
   ```bash
   cd backend
   uv sync
   ```

3. Set environment variables:
   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.local
   export SECRET_KEY=dev-secret-key
   export DEBUG=True
   export POSTGRES_DB=plantops
   export POSTGRES_USER=plantops
   export POSTGRES_PASSWORD=plantops
   export POSTGRES_HOST=localhost
   export POSTGRES_PORT=5432
   export CELERY_BROKER_URL=amqp://plantops:plantops@localhost:5672//
   export CELERY_RESULT_BACKEND=redis://localhost:6379/1
   ```

4. Run migrations:
   ```bash
   python manage.py migrate_schemas --shared
   python manage.py migrate_schemas --tenant
   ```

5. Create a superuser (optional):
   ```bash
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```bash
   python manage.py runserver
   ```

### Frontend

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```

2. Start the dev server:
   ```bash
   npm run dev
   ```

## Migrations

Because we use django-tenants, migrations must be run for both shared and tenant schemas:

```bash
# Shared schema (public)
python manage.py migrate_schemas --shared

# All tenant schemas
python manage.py migrate_schemas --tenant
```

## Creating a Demo Tenant

```bash
python manage.py shell
```

```python
from apps.tenants.services import create_tenant

tenant = create_tenant(
    name="Demo Corp",
    slug="demo",
    schema_name="demo",
    domain="demo.localhost",
)
print(f"Tenant created: {tenant.name} (schema: {tenant.schema_name})")
```

## Running Tests

```bash
cd backend
pytest
```

## Project Structure

```
.
├── backend/
│   ├── apps/
│   │   ├── tenants/       # Tenant provisioning (shared schema)
│   │   ├── accounts/      # Users, roles, auth
│   │   ├── locations/     # Physical sites
│   │   ├── planters/      # Containers, inventory
│   │   ├── plants/        # Species, care profiles
│   │   ├── devices/       # IoT device registry
│   │   ├── measurements/  # Raw sensor readings
│   │   ├── alerts/        # Alert definitions and instances
│   │   ├── tasks/         # Gardener tasks
│   │   ├── notifications/ # Email, SMS, push
│   │   ├── billing/       # Subscriptions, invoices
│   │   └── audit/         # Audit trails
│   ├── config/            # Settings, URLs, WSGI, ASGI, Celery
│   ├── templates/         # HTMX base templates
│   ├── static/            # Static assets
│   ├── locale/            # Translation files
│   ├── tests/             # Pytest tests
│   └── docs/              # Architecture and governance docs
├── frontend/
│   └── src/
│       ├── modules/
│       │   ├── dashboard/  # Overview, KPIs
│       │   ├── expert/     # Analytics
│       │   └── realtime/   # Live data
│       └── i18n/           # Translations
└── infra/
    ├── docker/             # Dockerfiles
    ├── nginx/              # Reverse proxy
    ├── postgres/           # Init scripts
    ├── prometheus/         # Metrics config
    └── grafana/            # Dashboard configs
```

## Frontend Boundaries

- **HTMX + Django Templates**: Admin, CRUD, forms, task lists
- **React + Vite**: Dashboard, expert analytics, realtime charts

See [docs/architecture/FRONTEND_BOUNDARIES.md](backend/docs/architecture/FRONTEND_BOUNDARIES.md).

## Bounded Contexts

Each Django app is a bounded context with DDD structure:
- `models.py` — Domain entities
- `services.py` — Write operations
- `selectors.py` — Read operations
- `events.py` — Domain events

See [docs/architecture/DDD_OVERVIEW.md](backend/docs/architecture/DDD_OVERVIEW.md).

## Governance

See [docs/governance/RULES.md](backend/docs/governance/RULES.md).

## License

Proprietary — All rights reserved.
