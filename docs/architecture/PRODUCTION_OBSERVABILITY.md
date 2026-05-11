# Production Deployment & Observability

Phase 17 adds production-grade observability, health monitoring, metrics,
structured logging, and deployment hardening.

## Observability Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Flower Backend                       │
│                                                      │
│  /health/live/     → liveness probe                 │
│  /health/ready/    → readiness probe (DB, Redis)    │
│  /health/          → aggregate health summary       │
│  /metrics          → django-prometheus metrics      │
│                                                      │
│  Logging: JSON formatter → stdout → Loki / ELK     │
│  Sentry: Error tracking + performance tracing       │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                 Prometheus                           │
│  Scrape targets: backend, celery, postgres, redis   │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                 Grafana                              │
│  Dashboards: API, Celery, Notifications, SLA, Sync  │
└─────────────────────────────────────────────────────┘
```

## Logging Strategy

| Environment | Format | Shipper |
|-------------|--------|---------|
| Development | Console (default Django) | — |
| Production | JSON (via `JSONLogFormatter`) | Loki / ELK / stdout |

**`LOG_FORMAT`** setting controls the format:
- `console` → human-readable
- `json` → structured JSON lines

Every log entry includes:
- `timestamp`, `level`, `logger`, `message`
- `request_id`, `correlation_id` (if available)
- `tenant_schema`, `user_id` (if available)
- `path`, `method`, `status_code`, `duration_ms` (API requests)

**Never logged:** auth tokens, push tokens, HMAC secrets, SMTP passwords, API keys.

## Healthcheck Strategy

| Endpoint | Type | Returns |
|----------|------|---------|
| `/health/live/` | Liveness | `{"status": "alive"}` — immediate |
| `/health/ready/` | Readiness | DB + Redis + Celery check |
| `/health/` | Summary | Aggregate status + all checks |

Healthcheck format:
```json
{
    "status": "healthy",
    "checks": {
        "database": {"status": "healthy", "detail": "..."},
        "redis": {"status": "healthy", "detail": "..."},
        "celery": {"status": "degraded", "detail": "No workers"}
    },
    "timestamp": "2026-05-11T12:00:00+00:00"
}
```

## Metrics & Grafana

### Prometheus Scrape Targets

| Job | Target | Port |
|-----|--------|------|
| `django` | `backend:8000` | `/metrics` |
| `celery` | `flower:5555` | `/metrics` |
| `postgres` | `postgres-exporter:9187` | — |
| `redis` | `redis-exporter:9121` | — |
| `nginx` | `nginx:9113` | — |

### Grafana Dashboards

| Dashboard | Metrics |
|-----------|---------|
| API Overview | Request latency, error rate, throughput |
| Celery Overview | Queue depth, active workers, failed tasks |
| Notification Pipeline | Retry count, dead letter count, throughput |
| SLA & Escalation | Breach rate, escalation level, overdue count |
| Sync Engine | Sync duration, failures, checkpoint age |
| Tenant Activity | Per-tenant request count, error rate |

## Metrics Abstraction

`core/metrics/__init__.py` provides three primitives:

| Function | Type | Example |
|----------|------|---------|
| `increment_counter(name, value)` | Counter | API requests |
| `observe_duration(name, seconds)` | Histogram | Request latency |
| `set_gauge(name, value)` | Gauge | Active connections |

These are in-memory by default and can be exported to Prometheus via
`django-prometheus` middleware when `METRICS_ENABLED=True`.

## Sentry Integration

| Setting | Purpose |
|---------|---------|
| `SENTRY_DSN` | Sentry project DSN |
| `SENTRY_ENVIRONMENT` | `production` / `staging` / `development` |
| `SENTRY_TRACES_SAMPLE_RATE` | Performance tracing rate (0.0–1.0) |

Attached tags: `request_id`, `correlation_id`, `tenant_schema`.

## Docker Compose Hardening

| Service | Healthcheck | Restart | Depends |
|---------|-------------|---------|---------|
| postgres | `pg_isready` | unless-stopped | — |
| redis | `redis-cli ping` | unless-stopped | — |
| backend | `/health/live/` | unless-stopped | postgres, redis |
| celery_worker | — | unless-stopped | redis |
| celery_beat | — | unless-stopped | redis |

## Security Notes

- `/metrics` endpoint should not be public in production — protect via Nginx
  IP allowlist or environment flag `METRICS_ENABLED`
- Grafana admin password set via `GRAFANA_ADMIN_PASSWORD`
- Sentry DSN is not sensitive (it's a public URL), but should not be logged
- Nginx rate limiting and security headers are placeholder

## Files

| File | Purpose |
|------|---------|
| `core/metrics/__init__.py` | Metrics abstraction (counter, gauge, histogram) |
| `core/logging/json_formatter.py` | JSON log formatter |
| `core/services/runtime_health_service.py` | DB/Redis/Celery health checks |
| `core/views.py` | Healthcheck endpoints |
| `config/urls.py` | Healthcheck route registration |
| `infra/prometheus/prometheus.yml` | Prometheus scrape config |
| `infra/grafana/dashboards/` | Grafana dashboard JSON stubs |
