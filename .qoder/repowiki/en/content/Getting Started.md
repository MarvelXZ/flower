# Getting Started

<cite>
**Referenced Files in This Document**
- [README.md](file://README.md)
- [docker-compose.yml](file://docker-compose.yml)
- [backend/pyproject.toml](file://backend/pyproject.toml)
- [backend/manage.py](file://backend/manage.py)
- [backend/config/settings/base.py](file://backend/config/settings/base.py)
- [backend/config/settings/local.py](file://backend/config/settings/local.py)
- [backend/config/settings/production.py](file://backend/config/settings/production.py)
- [backend/config/settings/test.py](file://backend/config/settings/test.py)
- [backend/apps/tenants/services.py](file://backend/apps/tenants/services.py)
- [backend/apps/tenants/models.py](file://backend/apps/tenants/models.py)
- [infra/docker/backend/Dockerfile](file://infra/docker/backend/Dockerfile)
- [infra/docker/frontend/Dockerfile](file://infra/docker/frontend/Dockerfile)
- [frontend/package.json](file://frontend/package.json)
- [frontend/vite.config.ts](file://frontend/vite.config.ts)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Environment Setup](#environment-setup)
5. [Installation Methods](#installation-methods)
6. [Database Configuration and Migrations](#database-configuration-and-migrations)
7. [Demo Tenant Creation](#demo-tenant-creation)
8. [Verification Checklist](#verification-checklist)
9. [Troubleshooting](#troubleshooting)
10. [Operating System Notes](#operating-system-notes)
11. [Conclusion](#conclusion)

## Introduction
This guide helps new developers and users set up the PlantOps/PlanterOps SaaS platform locally. It covers prerequisites, Docker-based and local development installations, environment configuration, dependency management, database setup, tenant creation, and verification steps. The platform uses Python 3.12+, Node.js, Docker, and PostgreSQL with multi-tenant schemas powered by django-tenants.

## Prerequisites
- Python 3.12+ (required by the backend)
- Node.js 20+ (required by the frontend)
- Docker and Docker Compose (recommended for full-stack setup)
- PostgreSQL 16+ (required for the database)
- uv (Python package manager used by the backend)
- npm (Node package manager used by the frontend)

These requirements are reflected in the project’s tech stack and configuration files.

**Section sources**
- [README.md:7-10](file://README.md#L7-L10)
- [backend/pyproject.toml:6](file://backend/pyproject.toml#L6)
- [infra/docker/backend/Dockerfile:10](file://infra/docker/backend/Dockerfile#L10)
- [infra/docker/frontend/Dockerfile:10](file://infra/docker/frontend/Dockerfile#L10)

## Quick Start
Choose one of the two installation approaches below.

- Docker-based quick start: Start all services with Docker Compose, then access the backend API, frontend, admin, and monitoring dashboards.
- Local development quick start: Install uv and npm, configure environment variables, run migrations, and start the backend and frontend servers.

**Section sources**
- [README.md:12-35](file://README.md#L12-L35)
- [README.md:36-93](file://README.md#L36-L93)

## Environment Setup
Set environment variables for local development. The backend loads configuration from environment variables and supports separate settings modules for local, production, and test environments.

Key environment variables used by the backend include:
- DJANGO_SETTINGS_MODULE
- SECRET_KEY
- DEBUG
- POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
- CELERY_BROKER_URL
- CELERY_RESULT_BACKEND

The frontend expects VITE_API_BASE_URL to point to the backend API.

**Section sources**
- [README.md:51-63](file://README.md#L51-L63)
- [backend/config/settings/base.py:155-164](file://backend/config/settings/base.py#L155-L164)
- [backend/config/settings/base.py:273-274](file://backend/config/settings/base.py#L273-L274)
- [backend/manage.py:10](file://backend/manage.py#L10)
- [frontend/vite.config.ts:28](file://frontend/vite.config.ts#L28)

## Installation Methods
There are two recommended installation methods: Docker-based and local development.

### Docker-Based Installation
1. Copy the environment file and start services:
   - Copy the example environment file to .env
   - Bring up all services with Docker Compose
2. Access the services:
   - Backend API endpoints
   - API documentation (Swagger)
   - Django Admin
   - Frontend development server
   - RabbitMQ Management
   - Flower (Celery monitoring)
   - PgAdmin

Docker Compose defines services for PostgreSQL, Redis, RabbitMQ, Django backend, Celery worker and scheduler, Nginx reverse proxy, and PgAdmin. Ports are exposed as defined in the compose file.

**Section sources**
- [README.md:16-24](file://README.md#L16-L24)
- [README.md:26-35](file://README.md#L26-L35)
- [docker-compose.yml:7-26](file://docker-compose.yml#L7-L26)
- [docker-compose.yml:47-70](file://docker-compose.yml#L47-L70)
- [docker-compose.yml:74-104](file://docker-compose.yml#L74-L104)
- [docker-compose.yml:106-132](file://docker-compose.yml#L106-L132)
- [docker-compose.yml:134-161](file://docker-compose.yml#L134-L161)
- [docker-compose.yml:163-183](file://docker-compose.yml#L163-L183)
- [docker-compose.yml:185-202](file://docker-compose.yml#L185-L202)
- [docker-compose.yml:204-222](file://docker-compose.yml#L204-L222)
- [docker-compose.yml:224-248](file://docker-compose.yml#L224-L248)

### Local Development Installation
Backend (Python + uv):
1. Install uv
2. Sync dependencies in the backend directory
3. Set environment variables for local development
4. Run migrations for shared and tenant schemas
5. Optionally create a superuser
6. Start the development server

Frontend (Node.js + npm):
1. Install dependencies in the frontend directory
2. Start the development server

**Section sources**
- [README.md:40-49](file://README.md#L40-L49)
- [README.md:51-79](file://README.md#L51-L79)
- [README.md:83-92](file://README.md#L83-L92)

## Database Configuration and Migrations
The backend uses PostgreSQL with django-tenants for multi-tenant schemas. The base settings load database credentials from environment variables. Because of multi-tenancy, migrations must be applied to both shared and tenant schemas.

- Shared schema (public): migrate_schemas --shared
- All tenant schemas: migrate_schemas --tenant

The Docker Compose setup runs migrations automatically when the backend starts.

**Section sources**
- [README.md:96-104](file://README.md#L96-L104)
- [backend/config/settings/base.py:155-164](file://backend/config/settings/base.py#L155-L164)
- [docker-compose.yml:100-103](file://docker-compose.yml#L100-L103)

## Demo Tenant Creation
After the database is initialized, create a demo tenant using the provided tenant service. The tenant creation process provisions a new schema and sets up the primary domain for routing.

Steps:
1. Open the Django shell
2. Import the tenant creation service
3. Call the service with tenant details (name, slug, schema_name, domain)
4. Confirm the tenant was created

**Section sources**
- [README.md:106-123](file://README.md#L106-L123)
- [backend/apps/tenants/services.py:11-35](file://backend/apps/tenants/services.py#L11-L35)
- [backend/apps/tenants/models.py:6](file://backend/apps/tenants/models.py#L6)

## Verification Checklist
Ensure all services are reachable and functioning after installation:

- Backend API: http://localhost:8000/api/
- API Docs (Swagger): http://localhost:8000/api/docs/
- API Schema: http://localhost:8000/api/schema/
- Django Admin: http://localhost:8000/admin/
- Frontend (Vite): http://localhost:5173/
- RabbitMQ Management: http://localhost:15672/
- Flower (Celery): http://localhost:5555/
- PgAdmin: http://localhost:5050/

Additionally, confirm:
- PostgreSQL is healthy and accepting connections
- Redis is reachable
- RabbitMQ is running and accessible
- Celery worker and beat are running
- Nginx proxies requests correctly
- Frontend can reach the backend API via the configured proxy

**Section sources**
- [README.md:26-35](file://README.md#L26-L35)
- [docker-compose.yml:18-24](file://docker-compose.yml#L18-L24)
- [docker-compose.yml:39-43](file://docker-compose.yml#L39-L43)
- [docker-compose.yml:63-67](file://docker-compose.yml#L63-L67)
- [docker-compose.yml:90](file://docker-compose.yml#L90)
- [docker-compose.yml:177](file://docker-compose.yml#L177)
- [frontend/vite.config.ts:15-20](file://frontend/vite.config.ts#L15-L20)

## Troubleshooting
Common issues and resolutions:

- Port conflicts:
  - The backend binds to 8000, frontend to 5173, PostgreSQL to 5432, Redis to 6379, RabbitMQ to 5672/15672, Nginx to 80, PgAdmin to 5050, and Flower to 5555. Stop conflicting services or adjust ports in the compose file.
  
- Dependency problems:
  - Backend: Ensure uv is installed and dependencies are synced in the backend directory.
  - Frontend: Ensure npm is installed and dependencies are installed in the frontend directory.
  
- Database connectivity:
  - Verify POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, and POSTGRES_PORT match your environment.
  - Confirm migrations were run for both shared and tenant schemas.
  
- Celery and message queue:
  - Ensure RabbitMQ and Redis are healthy and reachable.
  - Confirm CELERY_BROKER_URL and CELERY_RESULT_BACKEND are set correctly.
  
- CORS and origins:
  - For local development, ensure ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS/CORS_ALLOWED_ORIGINS include localhost and frontend origin.

**Section sources**
- [README.md:40-49](file://README.md#L40-L49)
- [README.md:83-92](file://README.md#L83-L92)
- [README.md:51-63](file://README.md#L51-L63)
- [backend/config/settings/base.py:155-164](file://backend/config/settings/base.py#L155-L164)
- [backend/config/settings/base.py:273-274](file://backend/config/settings/base.py#L273-L274)
- [backend/config/settings/local.py:7-14](file://backend/config/settings/local.py#L7-L14)
- [docker-compose.yml:18-24](file://docker-compose.yml#L18-L24)
- [docker-compose.yml:39-43](file://docker-compose.yml#L39-L43)
- [docker-compose.yml:63-67](file://docker-compose.yml#L63-L67)

## Operating System Notes
- Windows: Use PowerShell or Command Prompt. Docker Desktop for Windows is recommended. Ensure WSL2 backend is enabled if needed.
- macOS: Use Terminal. Docker Desktop for Mac is recommended.
- Linux: Use your distribution’s terminal. Docker and Docker Compose must be installed.

Environment variables and commands shown in this guide are shell-agnostic but assume POSIX-style environment variable setting. On Windows, use the equivalent PowerShell or Command Prompt syntax.

## Conclusion
You now have the essential steps to install and run the PlantOps/PlanterOps platform either with Docker Compose for a full-stack environment or in local development mode. After completing the setup, verify all services, create a demo tenant, and explore the API, admin interface, and frontend dashboard.