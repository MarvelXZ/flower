# PlantOps Engineering Audit & Implementation Plan

**Auditor**: Staff/Principal Software Engineer Review
**Date**: 2026-05-08
**Scope**: Full codebase discovery, gap analysis, architecture direction

---

## A. Existing Codebase Summary

### What Exists (Confirmed Facts)

#### 1. Project Structure
- Multi-root layout: `backend/`, `frontend/`, `infra/`, root-level compose files
- `.env` and `.env.example` present with comprehensive variable coverage
- `.gitignore` is thorough (covers Python, Node, Docker, IDE artifacts)

#### 2. Backend Foundation
- **Python**: 3.12+ configured, uv as package manager
- **Django**: 5.x with 4-tier settings (`base`, `local`, `production`, `test`)
- **Multi-tenancy**: django-tenants configured with `TenantMainMiddleware`, schema routing
- **Tenant models**: `Client` (TenantMixin) and `Domain` (DomainMixin) in `apps.tenants`
- **Services**: `create_tenant()`, `deactivate_tenant()` with transaction wrapping
- **Celery**: Configured with RabbitMQ broker, Redis result backend, beat scheduler
- **DRF**: Installed with `drf-spectacular` for OpenAPI schema generation
- **i18n**: 8 languages configured (`sr`, `en`, `hr`, `sl`, `mk`, `sq`, `el`, `de`)
- **django-modeltranslation**: Registered with fallback to `sr` -> `en`
- **Security headers**: `X_FRAME_OPTIONS`, `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`
- **Lint/Format**: Ruff configured with Google docstring convention
- **Tests**: pytest-django configured, `conftest.py` with tenant fixtures

#### 3. Bounded Contexts (12 apps)
All apps have the DDD skeleton: `models.py`, `services.py`, `selectors.py`, `events.py`, `admin.py`, `apps.py`, `tests/__init__.py`

| App | Status | Models |
|-----|--------|--------|
| `tenants` | Functional | `Client`, `Domain` with admin |
| `accounts` | Skeleton | `UserProfile` (placeholder, no fields) |
| `locations` | Skeleton | `Location` (placeholder, no fields) |
| `planters` | Skeleton | `Planter` (placeholder, no fields) |
| `plants` | Skeleton | `PlantSpecies` (placeholder, no fields) + `translation.py` |
| `devices` | Skeleton | `Device` (placeholder, no fields) |
| `measurements` | Skeleton | `RawReading` (placeholder, no fields) |
| `alerts` | Skeleton | `Alert` (placeholder, no fields) |
| `tasks` | Skeleton | `Task` (placeholder, no fields) |
| `notifications` | Skeleton | `NotificationLog` (placeholder, no fields) |
| `billing` | Skeleton | `Subscription` (placeholder, no fields) |
| `audit` | Skeleton | `AuditLog` (placeholder, no fields) |

#### 4. Docker / Infrastructure
- `docker-compose.yml` with 9 services: backend, frontend, postgres:16, redis, rabbitmq, celery_worker, celery_beat, nginx, pgadmin, flower
- `docker-compose.override.yml` for local dev overrides
- Backend Dockerfile: multi-stage (base, development, production) using `ghcr.io/astral-sh/uv:python3.12-bookworm`
- Frontend Dockerfile: multi-stage (base, deps, development, build, production)
- Nginx config: routes `/api/`, `/admin/` to backend, everything else to frontend dev server
- Healthchecks on postgres, redis, rabbitmq

#### 5. Frontend
- Vite + React 18 + TypeScript scaffolded
- i18next with `sr` and `en` locale files
- React Router mounted at root
- Module directories: `dashboard/`, `expert/`, `realtime/` (all empty)

#### 6. Documentation
- `README.md` with setup instructions
- `docs/INDEX.md` with navigation
- `docs/architecture/DDD_OVERVIEW.md` — bounded context definitions
- `docs/architecture/MULTI_TENANCY.md` — tenant isolation docs
- `docs/architecture/IOT_INGEST.md` — telemetry pipeline design
- `docs/architecture/FRONTEND_BOUNDARIES.md` — HTMX vs React rules
- `docs/governance/RULES.md` — 10 governance rules
- `docs/governance/AUDIT_CHECKLIST.md` — release checklist

#### 7. Tests
- `tests/test_startup.py` — settings sanity checks
- `tests/test_tenants.py` — tenant service tests
- `conftest.py` — `public_tenant`, `demo_tenant`, `use_tenant_context` fixtures

---

### What Is Missing

#### Critical (Blocks MVP)
1. **No migrations exist** — Only `migrations/__init__.py` files; no actual schema
2. **No custom User model** — Using Django default; will be painful to change later
3. **No device credential system** — Devices cannot authenticate
4. **No telemetry ingest endpoint** — Raw sensor data has nowhere to land
5. **No MQTT broker** — Docker Compose has RabbitMQ (for Celery) but no MQTT broker (Mosquitto/EMQ)
6. **No API endpoints wired** — All DRF URLs are commented out in `config/urls.py`
7. **No serializers** — Zero DRF serializers across all apps
8. **No viewsets** — Zero DRF viewsets across all apps

#### Important (Needed for production readiness)
9. **No UUID primary keys** — All models use default `BigAutoField`
10. **No audit fields mixin** — No `created_by`/`updated_by` tracking
11. **No `django-guid` or request ID tracing**
12. **No structured logging configuration** — `structlog` in dependencies but unused
13. **No rate limiting** — Django Ratelimit not installed
14. **No health check endpoint** — No `/health/` or `/ready/` endpoint
15. **No prometheus metrics** — `prometheus.yml` exists but Django has no `django-prometheus`
16. **No API versioning strategy** — Commented paths suggest `v1/` but no policy defined
17. **No Makefile / task runner** — Common commands not scripted
18. **No pre-commit hooks** — `pre-commit` in dev deps but no `.pre-commit-config.yaml`
19. **No uv.lock** — Lockfile not generated
20. **No frontend package-lock.json** — Node lockfile missing

#### Architectural
21. **No automation bounded context** — Missing `apps.automation` for rules engine
22. **No firmware bounded context** — Device OTA firmware management not separated
23. **No `organizations` context** — Tenant = organization currently; may need separation later
24. **No event bus / outbox pattern** — `events.py` files contain only dataclass skeletons
25. **No tenant-aware Celery task base class** — Risk of forgetting `tenant_context()`
26. **No device provisioning flow** — No token generation, no QR-code pairing
27. **No alert rules engine** — Alert model is a placeholder; no threshold evaluation

---

### What Is Risky

1. **Default SECRET_KEY in base.py** — `env.str("SECRET_KEY", default="dev-secret-key-change-me")` means if env is missing, the app runs with a known secret. This is a **P0 security risk**.
2. **Placeholder models have `class Meta` but no `abstract = True`** — Django will create empty tables for all 12 apps on migrate. This is harmless but wasteful.
3. **Backend Dockerfile `uv pip install` may fail** — `pyproject.toml` references `manage:main` script but `manage.py` is not a module with `main()` function.
4. **Frontend proxy config uses `process.env`** — Vite configs run at build time; `process.env.VITE_API_BASE_URL` won't work as expected in `vite.config.ts`.
5. **No database connection pooling** — `CONN_MAX_AGE` only set in production; base has no pooling.
6. **CORS defaults to empty list** — `CORS_ALLOWED_ORIGINS = env.list(..., default=[])` means local dev without env vars has CORS completely disabled, which breaks frontend.
7. **Flower command in docker-compose is fragile** — Uses shell variable expansion inside a string that may not resolve correctly.
8. **No graceful shutdown for Celery** — Docker Compose sends SIGTERM but Celery workers need `--stopasap` or `shutdown()` for clean exit.
9. **Tenant schema auto-drop enabled** — `auto_drop_schema = True` on `Client` means deleting a tenant deletes its schema permanently. Dangerous in production.
10. **Debug toolbar loaded unconditionally in local** — `debug_toolbar_urls()` returns URLs even if app is not installed; could fail silently.

---

### What Should Stay

1. **The DDD file structure** — `models/services/selectors/events/admin` per app is solid
2. **django-tenants schema isolation** — Correct choice for 1000+ tenants
3. **The 12-app boundary split** — Contexts are well-defined and map to business capabilities
4. **Settings hierarchy** — Base + environment-specific is correct
5. **uv + pyproject.toml** — Modern Python packaging, keep it
6. **Docker Compose topology** — Services are correctly separated
7. **Ruff configuration** — Good lint rule selection
8. **pytest setup** — `conftest.py` with tenant fixtures is well-designed
9. **i18n language list** — Covers the target Balkan/Central European market
10. **Documentation structure** — `docs/architecture/` and `docs/governance/` is enterprise-grade

---

### What Should Be Refactored

1. **All placeholder models** — Need real fields, UUIDs, audit mixins, indexes
2. **`accounts` -> `users`** — Rename to match target architecture terminology
3. **`measurements` -> `telemetry`** — Rename to align with IoT domain language
4. **Add `automation` app** — Missing bounded context for rules engine
5. **Add `firmware` app** — Or merge into devices; currently not represented
6. **Frontend proxy config** — Fix `process.env` usage in `vite.config.ts`
7. **Docker Compose command strings** — Use array syntax where possible for better signal handling

---

### What Should NOT Be Touched Yet

1. **Go gateway** — Explicitly out of scope until Django core is stable
2. **Kubernetes** — Premature; Docker Compose is correct for this stage
3. **Microservices** — Monolith with bounded contexts is the right pattern now
4. **Advanced ML / prediction** — Not needed for MVP
5. **Stripe billing integration** — `billing` app should have models but no payment provider yet
6. **Mobile app** — Not in scope
7. **Advanced RBAC** — Basic roles (admin, gardener, expert) are enough for MVP

---

## B. Current Architecture Map

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx (port 80)                          │
│  /static → /srv/static      /media → /srv/media                 │
│  /api/* → backend:8000      /admin/* → backend:8000             │
│  /* → frontend:5173 (dev) or static build (prod)                │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│   Backend    │    │  Frontend       │    │  Flower      │
│  Django 5.x  │    │  Vite + React   │    │  Celery      │
│  port 8000   │    │  port 5173      │    │  port 5555   │
└──────────────┘    └─────────────────┘    └──────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────────┐
│                    django-tenants Middleware                │
│         Host header → Domain lookup → Schema switch         │
└────────────────────────────────────────────────────────────┘
        │
   ┌────┴────┬────────┬────────┬────────┐
   ▼         ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌─────────┐
│public│ │tenant│ │tenant│ │tenant│ │  tenant  │
│schema│ │schema│ │schema│ │schema│ │  schema  │
│      │ │ acme │ │ demo │ │ etc │ │   ...    │
└──────┘ └──────┘ └─────┘ └─────┘ └─────────┘
   │         │        │        │        │
   └─────────┴────────┴────────┴────────┘
              PostgreSQL 16
        │
        ▼
   ┌─────────┐  ┌─────────┐  ┌───────────┐
   │  Redis  │  │RabbitMQ │  │ Celery    │
   │  :6379  │  │ :5672   │  │ Worker    │
   │result   │  │ broker  │  │ + Beat    │
   └─────────┘  └─────────┘  └───────────┘
```

---

## C. P0/P1/P2/P3 Gap Analysis

### P0 — Must Fix Before Continuing

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| P0-1 | **No custom User model** | Changing User after first migrate is nearly impossible in Django | Create `apps.users.AbstractUser` subclass before any migration |
| P0-2 | **Default SECRET_KEY fallback** | App runs with known secret if env var missing | Remove default, raise `ImproperlyConfigured` if missing |
| P0-3 | **No device authentication** | Any client can POST telemetry | Add `DeviceCredential` model + API key middleware |
| P0-4 | **No telemetry ingest endpoint** | Sensor data has no landing point | Add `/api/v1/telemetry/ingest/` endpoint |
| P0-5 | **No MQTT broker in compose** | IoT devices cannot connect | Add Eclipse Mosquitto service |
| P0-6 | **All models are empty placeholders** | No business data can be stored | Implement core models: Device, Plant, TelemetryRecord, Alert |

### P1 — Should Fix During Foundation Phase

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| P1-1 | **No UUID primary keys** | Exposes internal DB sequence; harder to shard | Add `UUIDModel` base class with `uuid` PK |
| P1-2 | **No audit fields mixin** | No created_by/updated_by tracking | Add `AuditableModel` mixin |
| P1-3 | **No tenant-aware Celery base** | Risk of cross-tenant data leaks | Add `TenantTask` base class with automatic `tenant_context()` |
| P1-4 | **No rate limiting** | API vulnerable to brute force / DoS | Add `django-ratelimit` + middleware |
| P1-5 | **No health check endpoint** | Load balancers/orchestrators cannot verify liveness | Add `/health/`, `/ready/`, `/metrics/` endpoints |
| P1-6 | **No structured logging** | Hard to debug in production | Configure `structlog` with JSON formatter |
| P1-7 | **No `apps.automation`** | Cannot implement rules engine | Create automation bounded context |
| P1-8 | **No `apps.firmware`** | OTA updates not trackable | Create firmware bounded context |
| P1-9 | **CORS defaults to empty list** | Frontend cannot connect without env vars | Add sensible localhost defaults in `local.py` |
| P1-10 | **No API versioning policy** | Breaking changes will hurt consumers | Document and implement `/api/v1/` prefix strategy |

### P2 — Can Delay

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| P2-1 | **No pre-commit hooks** | Code quality depends on manual discipline | Add `.pre-commit-config.yaml` |
| P2-2 | **No uv.lock / package-lock.json** | Builds not perfectly reproducible | Generate lockfiles after dependency changes |
| P2-3 | **No Makefile** | Onboarding friction for common commands | Add `Makefile` with `make migrate`, `make test`, etc. |
| P2-4 | **No Sentry integration** | Production errors go unnoticed | Wire Sentry DSN from env |
| P2-5 | **No `django-guid`** | Cannot trace requests across services | Add GUID middleware |
| P2-6 | **No database indexes defined** | Queries will be slow at scale | Add indexes to query-heavy models |
| P2-7 | **Frontend proxy config bug** | May break API proxy in dev | Fix `vite.config.ts` to use `loadEnv` |
| P2-8 | **No graceful Celery shutdown** | Task loss on container restart | Add `stop_signal` and `stop_grace_period` |

### P3 — Future Improvement

| # | Gap | Impact | Fix |
|---|-----|--------|-----|
| P3-1 | **No event bus / outbox** | Domain events not reliably published | Implement outbox table + processor |
| P3-2 | **No TimescaleDB** | Telemetry tables will grow unbounded | Evaluate TimescaleDB for time-series |
| P3-3 | **No WebSocket support** | Realtime updates require polling | Add Django Channels or SSE |
| P3-4 | **No CDN for static files** | Static delivery from app server | Configure S3/CloudFront |
| P3-5 | **No terraform / IaC** | Infrastructure not versioned | Add Terraform configs |
| P3-6 | **No load testing suite** | Unknown performance limits | Add Locust/k6 tests |

---

## D. Recommended Backend Direction

### 1. App Restructuring

Rename to align with target architecture:

```
apps/
  tenants/        # KEEP — tenant provisioning
  users/          # RENAME from accounts — custom User + profiles
  organizations/  # NEW — tenant-level org settings (optional layer)
  locations/      # KEEP — physical sites
  planters/       # KEEP — containers
  plants/         # KEEP — species, care profiles
  devices/        # KEEP — device registry
  firmware/       # NEW — OTA updates, versions
  telemetry/      # RENAME from measurements — raw + processed
  alerts/         # KEEP — alert instances
  automation/     # NEW — rules engine
  tasks/          # KEEP — manual + system tasks
  notifications/  # KEEP — delivery logs
  billing/        # KEEP — subscriptions
  audit/          # KEEP — action logs
```

**Decision**: Do the rename now before migrations exist. After first migration, renames become expensive.

### 2. Model Base Classes

Create `apps.core` (or `apps.common`) with:

```python
class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class AuditableModel(UUIDModel):
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, ...)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, ...)

    class Meta:
        abstract = True
```

**Decision**: Add `apps.core` as a shared app (in `SHARED_APPS`). All tenant models inherit from `AuditableModel`.

### 3. Custom User Model

```python
# apps.users.models
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(choices=[("admin", "Admin"), ("gardener", "Gardener"), ("expert", "Expert")])
    language = models.CharField(default="sr")
    phone = models.CharField(blank=True)
    timezone = models.CharField(default="Europe/Belgrade")
```

**Decision**: Must be done BEFORE `migrate_schemas`. This is the #1 priority.

### 4. Tenant-Aware Celery

```python
# apps.core.celery
class TenantTask(Task):
    def __call__(self, *args, **kwargs):
        tenant_id = kwargs.pop("_tenant_id", None)
        if tenant_id:
            from django_tenants.utils import tenant_context
            from apps.tenants.models import Client
            tenant = Client.objects.get(id=tenant_id)
            with tenant_context(tenant):
                return self.run(*args, **kwargs)
        return self.run(*args, **kwargs)
```

Register in `config/celery.py`:
```python
app = Celery("plantops", task_cls="apps.core.celery.TenantTask")
```

### 5. API Structure

```
/api/v1/                # Versioned API
  /schema/              # OpenAPI schema (drf-spectacular)
  /docs/                # Swagger UI
  /auth/                # Authentication endpoints
  /users/               # User management
  /devices/             # Device CRUD
  /devices/{id}/telemetry/  # Device-specific telemetry
  /telemetry/           # Telemetry query/list
  /plants/              # Plant CRUD
  /planters/            # Planter CRUD
  /alerts/              # Alert list/acknowledge
  /tasks/               # Task CRUD
  /automation/rules/    # Automation rules
  /firmware/            # Firmware versions
```

---

## E. Recommended HTMX/React Frontend Direction

### HTMX Boundaries (Keep as canonical)

Use HTMX + Django templates for:
- `/admin/` and operator dashboards
- User management screens
- Location / planter / plant CRUD forms
- Task assignment and list views
- Alert acknowledgment UI
- Device pairing / provisioning wizard
- Billing subscription management

### React Islands (Use sparingly)

Use React ONLY for:
- `/dashboard/realtime/` — Live telemetry websocket dashboard
- `/dashboard/analytics/` — Historical charts, trends
- `/dashboard/devices/map/` — Device location map (if applicable)
- Embedded widgets in HTMX pages via `<div id="react-widget">` mount points

### Integration Pattern

```html
<!-- Django template -->
<div class="htmx-page">
  <h1>Device Detail</h1>
  <!-- HTMX for form updates -->
  <form hx-post="/api/v1/devices/{{ device.id }}/" hx-target="#device-form">
    ...
  </form>

  <!-- React island for realtime chart -->
  <div id="telemetry-chart"
       data-device-id="{{ device.id }}"
       data-api-token="{{ api_token }}">
  </div>
</div>

<script>
  // Mount React widget
  const el = document.getElementById('telemetry-chart');
  if (el) {
    mountTelemetryChart(el, {
      deviceId: el.dataset.deviceId,
      token: el.dataset.apiToken,
    });
  }
</script>
```

### Shared API Contract

Both HTMX and React consume the SAME DRF endpoints:
- HTMX: `hx-get="/api/v1/devices/"` + `hx-target` for HTML partial replacement
- React: `fetch('/api/v1/devices/')` + JSON parsing for component state

**Key rule**: API endpoints MUST support both JSON (for React) and HTML partial rendering (for HTMX) OR HTMX must handle JSON via client-side templates.

---

## F. Device + Telemetry Architecture

### Device Lifecycle

```
Factory Provisioning
      │
      ▼
┌─────────────────┐
│ DeviceCredential│  ← API key + secret generated server-side
│  (hashed)       │
└─────────────────┘
      │
      ▼
Pairing (QR scan / manual entry)
      │
      ▼
┌─────────────────┐
│   DeviceStatus  │  ← online/offline, last_seen, battery
└─────────────────┘
      │
      ▼
Telemetry Ingest
      │
      ▼
┌─────────────────┐
│ TelemetryRecord │  ← append-only, partitioned by time
└─────────────────┘
```

### Authentication Flow

1. Device boots with pre-flashed `device_id` and `provisioning_token`
2. Device calls `POST /api/v1/devices/provision/` with token
3. Server validates token, creates `DeviceCredential` with persistent `api_key`
4. Device stores `api_key` in NVS (non-volatile storage)
5. All subsequent requests include `X-Device-API-Key: <key>` header
6. Server middleware validates key against `DeviceCredential`

### Telemetry Ingest

```python
# POST /api/v1/telemetry/ingest/
# Headers: X-Device-API-Key: <key>
# Body: {
#   "schema_version": "1.0",
#   "device_id": "dev-abc123",
#   "message_id": "msg-uuid",
#   "timestamp": "2026-05-08T12:00:00Z",
#   "firmware_version": "1.2.3",
#   "readings": [
#     {"sensor": "soil_moisture", "value": 42.5, "unit": "percent"},
#     {"sensor": "temperature", "value": 23.1, "unit": "celsius"},
#   ]
# }

@api_view(["POST"])
@permission_classes([DeviceAPIKeyPermission])
def telemetry_ingest(request):
    # 1. Validate schema_version
    # 2. Validate message_id is unique (idempotency)
    # 3. Store raw payload as TelemetryRecord
    # 4. Enqueue Celery task for processing
    # 5. Return 202 Accepted
```

### Processing Pipeline

```
TelemetryRecord (raw)
      │
      ▼
Celery: process_telemetry_batch
      │
      ├── Validate sensor ranges
      ├── Handle time drift
      ├── Deduplicate by message_id
      └── Produce TelemetryBatch (aggregated)
      │
      ▼
Celery: evaluate_alert_rules
      │
      ├── Load alert rules for device/plant
      ├── Compare thresholds
      └── Create Alert if breached
      │
      ▼
Celery: create_tasks_from_alerts
      │
      └── Create Task for high-severity alerts
```

---

## G. Data Model Review/Proposal

### Core Base Classes

```python
# apps.core.models
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class AuditableModel(UUIDModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+%(class)s_created",
        verbose_name=_("created by"),
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="+%(class)s_updated",
        verbose_name=_("updated by"),
    )

    class Meta:
        abstract = True
```

### apps.users (renamed from accounts)

```python
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=20,
        choices=[
            ("admin", _("Administrator")),
            ("gardener", _("Gardener")),
            ("expert", _("Expert")),
        ],
        default="gardener",
        verbose_name=_("role"),
    )
    language = models.CharField(
        max_length=5,
        choices=settings.LANGUAGES,
        default="sr",
        verbose_name=_("language"),
    )
    phone = models.CharField(max_length=30, blank=True, verbose_name=_("phone"))
    timezone = models.CharField(max_length=50, default="Europe/Belgrade", verbose_name=_("timezone"))

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
```

### apps.devices

```python
class Device(AuditableModel):
    name = models.CharField(max_length=100, verbose_name=_("device name"))
    device_id = models.CharField(
        max_length=100, unique=True,
        verbose_name=_("hardware device ID"),
        help_text=_("Unique hardware identifier (e.g., MAC address, serial number)"),
    )
    device_type = models.CharField(
        max_length=50,
        choices=[("esp32", "ESP32"), ("esp8266", "ESP8266")],
        default="esp32",
        verbose_name=_("device type"),
    )
    firmware_version = models.CharField(max_length=50, blank=True, verbose_name=_("firmware version"))
    status = models.CharField(
        max_length=20,
        choices=[("online", _("Online")), ("offline", _("Offline")), ("provisioning", _("Provisioning"))],
        default="provisioning",
        verbose_name=_("status"),
    )
    last_seen_at = models.DateTimeField(null=True, blank=True, verbose_name=_("last seen at"))
    battery_level = models.FloatField(null=True, blank=True, verbose_name=_("battery level"))

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        indexes = [
            models.Index(fields=["status", "last_seen_at"]),
            models.Index(fields=["device_id"]),
        ]


class DeviceCredential(UUIDModel):
    device = models.OneToOneField(
        Device, on_delete=models.CASCADE,
        related_name="credential",
        verbose_name=_("device"),
    )
    api_key = models.CharField(max_length=255, unique=True, verbose_name=_("API key"))
    api_secret = models.CharField(max_length=255, verbose_name=_("API secret"))
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name=_("last used at"))

    class Meta:
        verbose_name = _("device credential")
        verbose_name_plural = _("device credentials")


class DeviceProvisioningToken(UUIDModel):
    device_id = models.CharField(max_length=100, unique=True, verbose_name=_("device ID"))
    token = models.CharField(max_length=255, unique=True, verbose_name=_("provisioning token"))
    expires_at = models.DateTimeField(verbose_name=_("expires at"))
    is_used = models.BooleanField(default=False, verbose_name=_("used"))

    class Meta:
        verbose_name = _("provisioning token")
        verbose_name_plural = _("provisioning tokens")
```

### apps.telemetry (renamed from measurements)

```python
class SensorType(UUIDModel):
    key = models.CharField(max_length=50, unique=True, verbose_name=_("sensor key"))
    name = models.CharField(max_length=100, verbose_name=_("sensor name"))
    unit = models.CharField(max_length=30, verbose_name=_("unit"))
    min_value = models.FloatField(null=True, blank=True, verbose_name=_("minimum value"))
    max_value = models.FloatField(null=True, blank=True, verbose_name=_("maximum value"))

    class Meta:
        verbose_name = _("sensor type")
        verbose_name_plural = _("sensor types")


class TelemetryRecord(UUIDModel):
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE,
        related_name="telemetry_records",
        verbose_name=_("device"),
    )
    sensor_type = models.ForeignKey(
        SensorType, on_delete=models.PROTECT,
        verbose_name=_("sensor type"),
    )
    value = models.FloatField(verbose_name=_("value"))
    measured_at = models.DateTimeField(db_index=True, verbose_name=_("measured at"))
    received_at = models.DateTimeField(auto_now_add=True, verbose_name=_("received at"))
    message_id = models.CharField(max_length=100, db_index=True, verbose_name=_("message ID"))
    raw_payload = models.JSONField(default=dict, verbose_name=_("raw payload"))
    firmware_version = models.CharField(max_length=50, blank=True, verbose_name=_("firmware version"))
    is_valid = models.BooleanField(default=True, verbose_name=_("valid"))
    validation_error = models.TextField(blank=True, verbose_name=_("validation error"))

    class Meta:
        verbose_name = _("telemetry record")
        verbose_name_plural = _("telemetry records")
        indexes = [
            models.Index(fields=["device", "sensor_type", "measured_at"]),
            models.Index(fields=["message_id"]),
        ]
        ordering = ["-measured_at"]


class TelemetryBatch(UUIDModel):
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE,
        related_name="telemetry_batches",
        verbose_name=_("device"),
    )
    period_start = models.DateTimeField(verbose_name=_("period start"))
    period_end = models.DateTimeField(verbose_name=_("period end"))
    sensor_type = models.ForeignKey(SensorType, on_delete=models.PROTECT, verbose_name=_("sensor type"))
    avg_value = models.FloatField(verbose_name=_("average value"))
    min_value = models.FloatField(verbose_name=_("minimum value"))
    max_value = models.FloatField(verbose_name=_("maximum value"))
    record_count = models.PositiveIntegerField(verbose_name=_("record count"))

    class Meta:
        verbose_name = _("telemetry batch")
        verbose_name_plural = _("telemetry batches")
        indexes = [
            models.Index(fields=["device", "sensor_type", "period_start"]),
        ]
```

### apps.plants

```python
class PlantType(AuditableModel):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    scientific_name = models.CharField(max_length=100, blank=True, verbose_name=_("scientific name"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    care_profile = models.JSONField(default=dict, verbose_name=_("care profile"))
    # care_profile structure:
    # {
    #   "soil_moisture": {"min": 30, "max": 70, "unit": "percent"},
    #   "temperature": {"min": 18, "max": 25, "unit": "celsius"},
    #   "light": {"min": 1000, "max": 50000, "unit": "lux"},
    # }

    class Meta:
        verbose_name = _("plant type")
        verbose_name_plural = _("plant types")


class Plant(AuditableModel):
    name = models.CharField(max_length=100, verbose_name=_("name"))
    plant_type = models.ForeignKey(
        PlantType, on_delete=models.PROTECT,
        related_name="plants",
        verbose_name=_("plant type"),
    )
    planter = models.ForeignKey(
        "planters.Planter", on_delete=models.CASCADE,
        related_name="plants",
        null=True, blank=True,
        verbose_name=_("planter"),
    )
    planted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("planted at"))
    notes = models.TextField(blank=True, verbose_name=_("notes"))
    is_active = models.BooleanField(default=True, verbose_name=_("active"))

    class Meta:
        verbose_name = _("plant")
        verbose_name_plural = _("plants")
```

### apps.alerts

```python
class AlertRule(AuditableModel):
    name = models.CharField(max_length=100, verbose_name=_("rule name"))
    plant_type = models.ForeignKey(
        "plants.PlantType", on_delete=models.CASCADE,
        related_name="alert_rules",
        verbose_name=_("plant type"),
    )
    sensor_type = models.ForeignKey(
        "telemetry.SensorType", on_delete=models.PROTECT,
        verbose_name=_("sensor type"),
    )
    condition = models.CharField(
        max_length=20,
        choices=[("lt", _("Less than")), ("gt", _("Greater than")), ("eq", _("Equals"))],
        verbose_name=_("condition"),
    )
    threshold = models.FloatField(verbose_name=_("threshold"))
    severity = models.CharField(
        max_length=20,
        choices=[("info", _("Info")), ("warning", _("Warning")), ("critical", _("Critical"))],
        default="warning",
        verbose_name=_("severity"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))

    class Meta:
        verbose_name = _("alert rule")
        verbose_name_plural = _("alert rules")


class Alert(UUIDModel):
    rule = models.ForeignKey(
        AlertRule, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alerts",
        verbose_name=_("rule"),
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE,
        related_name="alerts",
        verbose_name=_("device"),
    )
    plant = models.ForeignKey(
        "plants.Plant", on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alerts",
        verbose_name=_("plant"),
    )
    severity = models.CharField(max_length=20, verbose_name=_("severity"))
    message = models.TextField(verbose_name=_("message"))
    value_at_trigger = models.FloatField(null=True, blank=True, verbose_name=_("value at trigger"))
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="acknowledged_alerts",
        verbose_name=_("acknowledged by"),
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name=_("acknowledged at"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("resolved at"))
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("alert")
        verbose_name_plural = _("alerts")
        indexes = [
            models.Index(fields=["device", "severity", "created_at"]),
            models.Index(fields=["resolved_at", "created_at"]),
        ]
        ordering = ["-created_at"]
```

### apps.automation (NEW)

```python
class AutomationRule(AuditableModel):
    name = models.CharField(max_length=100, verbose_name=_("rule name"))
    trigger_type = models.CharField(
        max_length=50,
        choices=[
            ("alert_created", _("Alert Created")),
            ("telemetry_threshold", _("Telemetry Threshold")),
            ("schedule", _("Schedule")),
        ],
        verbose_name=_("trigger type"),
    )
    trigger_config = models.JSONField(default=dict, verbose_name=_("trigger configuration"))
    action_type = models.CharField(
        max_length=50,
        choices=[
            ("create_task", _("Create Task")),
            ("send_notification", _("Send Notification")),
            ("update_device", _("Update Device")),
        ],
        verbose_name=_("action type"),
    )
    action_config = models.JSONField(default=dict, verbose_name=_("action configuration"))
    is_active = models.BooleanField(default=True, verbose_name=_("active"))

    class Meta:
        verbose_name = _("automation rule")
        verbose_name_plural = _("automation rules")


class AutomationExecution(UUIDModel):
    rule = models.ForeignKey(
        AutomationRule, on_delete=models.CASCADE,
        related_name="executions",
        verbose_name=_("rule"),
    )
    status = models.CharField(
        max_length=20,
        choices=[("pending", _("Pending")), ("running", _("Running")), ("success", _("Success")), ("failed", _("Failed"))],
        default="pending",
        verbose_name=_("status"),
    )
    triggered_by = models.CharField(max_length=100, verbose_name=_("triggered by"))
    result = models.JSONField(default=dict, verbose_name=_("result"))
    error_message = models.TextField(blank=True, verbose_name=_("error message"))
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("automation execution")
        verbose_name_plural = _("automation executions")
```

### apps.firmware (NEW)

```python
class FirmwareVersion(AuditableModel):
    version = models.CharField(max_length=50, verbose_name=_("version"))
    device_type = models.CharField(
        max_length=50,
        choices=[("esp32", "ESP32"), ("esp8266", "ESP8266")],
        verbose_name=_("device type"),
    )
    binary = models.FileField(upload_to="firmware/", verbose_name=_("firmware binary"))
    changelog = models.TextField(blank=True, verbose_name=_("changelog"))
    is_stable = models.BooleanField(default=False, verbose_name=_("stable"))
    released_at = models.DateTimeField(auto_now_add=True, verbose_name=_("released at"))

    class Meta:
        verbose_name = _("firmware version")
        verbose_name_plural = _("firmware versions")
        unique_together = [("version", "device_type")]


class FirmwareUpdate(UUIDModel):
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE,
        related_name="firmware_updates",
        verbose_name=_("device"),
    )
    target_version = models.ForeignKey(
        FirmwareVersion, on_delete=models.PROTECT,
        verbose_name=_("target version"),
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", _("Pending")),
            ("downloading", _("Downloading")),
            ("flashing", _("Flashing")),
            ("rebooting", _("Rebooting")),
            ("completed", _("Completed")),
            ("failed", _("Failed")),
        ],
        default="pending",
        verbose_name=_("status"),
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, verbose_name=_("error message"))

    class Meta:
        verbose_name = _("firmware update")
        verbose_name_plural = _("firmware updates")
```

---

## H. MQTT Contract Proposal

### Broker Topology

```
Eclipse Mosquitto (port 1883, 8883 TLS)
  │
  ├── devices/{tenant_slug}/{device_id}/telemetry
  ├── devices/{tenant_slug}/{device_id}/heartbeat
  ├── devices/{tenant_slug}/{device_id}/status
  ├── devices/{tenant_slug}/{device_id}/ack
  │
  └── commands/{tenant_slug}/{device_id}/ota
  └── commands/{tenant_slug}/{device_id}/config
```

**Note**: `tenant_slug` in topic is for routing convenience ONLY. The server resolves the actual tenant from the device API key. The device does not know its tenant.

### Payload Schemas

#### Telemetry Message (v1.0)

```json
{
  "schema_version": "1.0",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_id": "dev-abc123",
  "timestamp": "2026-05-08T12:00:00Z",
  "firmware_version": "1.2.3",
  "readings": [
    {
      "sensor": "soil_moisture",
      "value": 42.5,
      "unit": "percent"
    },
    {
      "sensor": "temperature",
      "value": 23.1,
      "unit": "celsius"
    },
    {
      "sensor": "light",
      "value": 15000,
      "unit": "lux"
    },
    {
      "sensor": "battery",
      "value": 87.0,
      "unit": "percent"
    }
  ]
}
```

#### Heartbeat Message (v1.0)

```json
{
  "schema_version": "1.0",
  "message_id": "550e8400-e29b-41d4-a716-446655440001",
  "device_id": "dev-abc123",
  "timestamp": "2026-05-08T12:00:00Z",
  "firmware_version": "1.2.3",
  "uptime_seconds": 86400,
  "wifi_rssi": -65,
  "free_heap": 123456,
  "battery_level": 87.0
}
```

#### Status Message (v1.0)

```json
{
  "schema_version": "1.0",
  "message_id": "550e8400-e29b-41d4-a716-446655440002",
  "device_id": "dev-abc123",
  "timestamp": "2026-05-08T12:00:00Z",
  "status": "online",
  "error_code": null,
  "error_message": null
}
```

#### OTA Command (Server -> Device)

```json
{
  "schema_version": "1.0",
  "command_id": "550e8400-e29b-41d4-a716-446655440003",
  "type": "ota_update",
  "url": "https://cdn.plantops.local/firmware/esp32-1.3.0.bin",
  "expected_version": "1.3.0",
  "checksum_sha256": "abc123..."
}
```

#### OTA Ack (Device -> Server)

```json
{
  "schema_version": "1.0",
  "message_id": "550e8400-e29b-41d4-a716-446655440004",
  "device_id": "dev-abc123",
  "command_id": "550e8400-e29b-41d4-a716-446655440003",
  "timestamp": "2026-05-08T12:00:00Z",
  "status": "downloading",
  "progress_percent": 45
}
```

### Validation Rules

1. `schema_version` MUST be present and supported (currently `"1.0"`)
2. `message_id` MUST be a valid UUID v4; used for idempotency
3. `device_id` MUST match the authenticated device's `device_id`
4. `timestamp` MUST be ISO 8601 format; server tolerates +/- 5 minutes drift
5. `firmware_version` SHOULD be semantic versioning
6. Unknown fields in payload MUST be ignored (forward compatibility)
7. Missing optional fields MUST NOT cause rejection

### Authentication

- MQTT connections use TLS client certificates OR username/password
- Username = `device_id`
- Password = `api_key` (from `DeviceCredential`)
- Server validates credentials against `DeviceCredential` table
- Devices are rejected if `DeviceCredential.is_active = False`

---

## I. Implementation Roadmap

### Sprint 0: Foundation Hardening (Week 1)
1. Create `apps.core` with `UUIDModel`, `AuditableModel`, `TenantTask`
2. Rename `accounts` -> `users`, create custom `User` model
3. Rename `measurements` -> `telemetry`
4. Create `apps.automation` and `apps.firmware`
5. Remove default SECRET_KEY fallback
6. Add `django-ratelimit` to dependencies
7. Fix `vite.config.ts` proxy config
8. Generate `uv.lock` and `package-lock.json`
9. Create `.pre-commit-config.yaml`
10. Add Makefile with common commands

### Sprint 1: Device & Telemetry Core (Week 2)
1. Implement `Device`, `DeviceCredential`, `DeviceProvisioningToken`
2. Implement `SensorType`, `TelemetryRecord`, `TelemetryBatch`
3. Add device authentication middleware
4. Add `/api/v1/telemetry/ingest/` endpoint
5. Add MQTT broker (Mosquitto) to docker-compose
6. Add telemetry processing Celery task
7. Add device admin with credential management
8. Write tests for device services and telemetry ingest

### Sprint 2: Plants & Alerts (Week 3)
1. Implement `PlantType`, `Plant`
2. Implement `AlertRule`, `Alert`
3. Add alert evaluation engine (Celery task)
4. Add threshold configuration admin
5. Wire alert -> task creation
6. Write tests for alert evaluation

### Sprint 3: Frontend & Operations (Week 4)
1. Create HTMX device management screens
2. Create HTMX plant management screens
3. Create HTMX alert dashboard
4. Create React realtime telemetry widget
5. Add health check endpoint
6. Add prometheus metrics endpoint
7. Configure structlog JSON logging
8. Write integration tests

### Sprint 4: Automation & Polish (Week 5)
1. Implement `AutomationRule`, `AutomationExecution`
2. Implement `FirmwareVersion`, `FirmwareUpdate`
3. Add OTA command dispatch via MQTT
4. Add notification dispatch (email for MVP)
5. Add billing model limits enforcement
6. Performance testing with 100k telemetry records
7. Security review (API key rotation, rate limiting)
8. Documentation update

---

## J. First 10 Concrete Tasks

1. **T1**: Create `apps.core` with `UUIDModel`, `AuditableModel`, `TenantTask` base class
2. **T2**: Rename `accounts` -> `users` and create custom `User(AbstractUser)` with UUID PK
3. **T3**: Remove `default=` from `SECRET_KEY` in `base.py`; raise `ImproperlyConfigured` if missing
4. **T4**: Rename `measurements` -> `telemetry` and create real models: `SensorType`, `TelemetryRecord`
5. **T5**: Create real `Device` model with `device_id`, `status`, `firmware_version`, indexes
6. **T6**: Create `DeviceCredential` model and device API key authentication middleware
7. **T7**: Add `/api/v1/telemetry/ingest/` DRF endpoint with device auth and idempotency
8. **T8**: Add `apps.automation` with `AutomationRule` and `AutomationExecution` models
9. **T9**: Add `apps.firmware` with `FirmwareVersion` and `FirmwareUpdate` models
10. **T10**: Add Eclipse Mosquitto to `docker-compose.yml` with persistence and auth config

---

## K. Risks and Anti-Patterns to Avoid

### Risks

1. **Custom User model delay** — If we migrate with default User, changing later requires data migration hell. **Fix now.**
2. **Schema bloat** — Empty placeholder models create tables on migrate. Clean up before first real migration.
3. **Tenant context leaks in Celery** — Every background task MUST wrap in `tenant_context()`. One omission = data leak.
4. **Telemetry table growth** — `TelemetryRecord` will grow fast. Plan partitioning strategy early.
5. **MQTT auth complexity** — Device credential rotation without bricking devices is hard. Design for hot rotation.
6. **Alert storm** — A faulty sensor can generate thousands of alerts. Add deduplication and rate limiting.
7. **React scope creep** — Team may want to build everything in React. Stick to the HTMX-first rule.

### Anti-Patterns to Avoid

1. **Do NOT use BigAutoField for business entities** — UUIDs prevent enumeration attacks and make sharding easier.
2. **Do NOT trust device-provided tenant_id** — Always resolve tenant server-side from `DeviceCredential`.
3. **Do NOT update telemetry records** — Append-only. Mark invalid, never delete.
4. **Do NOT put business logic in views or serializers** — Views call services. Services contain logic.
5. **Do NOT create cross-app foreign keys** — Use IDs and events. Keeps contexts decoupled.
6. **Do NOT ignore timezone** — All device timestamps must be handled with `USE_TZ=True` awareness.
7. **Do NOT hardcode sensor types** — Use `SensorType` table. New sensors should not require code changes.
8. **Do NOT skip tests for "simple" models** — Every model, service, and selector gets a test.
9. **Do NOT commit `.env`** — Already in `.gitignore`, but verify team discipline.
10. **Do NOT build microservices yet** — The monolith with bounded contexts is correct for 1000 tenants.
