# Flower Backend

Django backend for the Flower multi-tenant SaaS platform.

The backend uses django-tenants with `SHARED_APPS` and `TENANT_APPS`, Django REST Framework, django-filter, drf-spectacular, Celery, Redis, PostgreSQL/PostGIS, and MQTT integration placeholders.

Bounded contexts live under `apps/`. Each context keeps models, services, selectors, API code, domain policies, events, tasks, admin registrations, migrations, and tests in separate packages.
