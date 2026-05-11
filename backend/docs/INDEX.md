# PlantOps Documentation Index

Welcome to the PlantOps documentation. This is the starting point for understanding the architecture, conventions, and operational procedures of the PlantOps SaaS platform.

## Quick Links

| Topic | File |
|---|---|
| DDD Overview & Bounded Contexts | [architecture/DDD_OVERVIEW.md](architecture/DDD_OVERVIEW.md) |
| Multi-Tenancy Architecture | [architecture/MULTI_TENANCY.md](architecture/MULTI_TENANCY.md) |
| IoT Ingest Pipeline | [architecture/IOT_INGEST.md](architecture/IOT_INGEST.md) |
| Frontend Boundaries | [architecture/FRONTEND_BOUNDARIES.md](architecture/FRONTEND_BOUNDARIES.md) |
| Governance Rules | [governance/RULES.md](governance/RULES.md) |
| Audit Checklist | [governance/AUDIT_CHECKLIST.md](governance/AUDIT_CHECKLIST.md) |

## Project Structure

```
backend/
  apps/              # Bounded contexts (DDD)
  config/            # Django settings, URLs, WSGI, ASGI, Celery
  templates/         # Django templates (HTMX)
  static/            # Static assets
  locale/            # Translation files
  tests/             # Pytest configuration and tests
  docs/              # This documentation
frontend/
  src/               # React / Vite source
infra/
  docker/            # Dockerfiles
  nginx/             # Reverse proxy config
  postgres/          # Init scripts
  prometheus/        # Metrics scraping config
  grafana/           # Dashboard configs
```

## Getting Started

1. See [README.md](../../README.md) for setup instructions.
2. Read [governance/RULES.md](governance/RULES.md) before writing code.
3. Understand [architecture/DDD_OVERVIEW.md](architecture/DDD_OVERVIEW.md) before adding models.
