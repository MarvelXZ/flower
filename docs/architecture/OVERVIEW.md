# Architecture Overview

Flower is a modular monolith built on Django, django-tenants, Django REST Framework, Celery, Redis, PostgreSQL/PostGIS, and MQTT. The platform supports owner tenants, provider tenants, hybrid tenants, public marketplace discovery, IoT telemetry ingest, and future mobile apps.

The owner tenant is the canonical source of truth for locations, plants, pots, devices, sensor readings, and care state. Provider tenants receive only synchronized copies of permitted owner data through explicit B2B APIs and outbox delivery. They never read owner schemas directly.

The backend is organized into bounded contexts under `backend/apps/`. Each context owns its models, service layer, selectors, API package, domain policies, events, tasks, admin registration, migrations, and tests. This keeps Flower deployable as one Django application while preserving clear domain boundaries.

Public schema data is reserved for tenant bootstrap, domains, and marketplace discovery. Tenant schemas hold operational data and integration secrets. Long-running and cross-tenant integration workflows are handled through Celery and explicit outbox records.
