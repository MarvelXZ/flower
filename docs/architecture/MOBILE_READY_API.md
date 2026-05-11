# Mobile-ready Provider Dashboard API

Phase 16 transforms the provider dashboard API into a production-grade,
mobile-ready layer with pagination, filtering, sorting, compact payloads,
throttling, versioning, and OpenAPI documentation.

## API Versioning

All provider API endpoints are versioned via URL path:

| Prefix | Scope | Auth |
|--------|-------|------|
| `/api/provider/v1/` | Provider dashboard | Session/token placeholder |
| `/api/b2b/v1/` | Owner → provider B2B | HMAC |

## Pagination

Uses DRF ``LimitOffsetPagination``:

| Parameter | Default | Max |
|-----------|---------|-----|
| `limit` | 20 | 100 |
| `offset` | 0 | — |

Response envelope:

```json
{
    "results": [...],
    "count": 123,
    "next": "?limit=20&offset=20",
    "previous": null,
    "meta": {
        "generated_at": "2026-05-11T12:00:00+00:00",
        "compact": true
    }
}
```

## Filtering

Supported query parameters on `/api/provider/v1/tasks/`:

| Param | Example | Description |
|-------|---------|-------------|
| `status` | `?status=open` | Filter by task status |
| `priority` | `?priority=urgent` | Filter by priority |
| `task_type` | `?task_type=watering` | Filter by task type |
| `assignee_id` | `?assignee_id=worker-1` | Filter by assignee |
| `overdue` | `?overdue=true` | Only overdue tasks |
| `breached` | `?breached=true` | Only SLA-breached tasks |
| `created_after` | `?created_after=2026-01-01` | Created after date |
| `created_before` | `?created_before=2026-06-01` | Created before date |

## Sorting

| Param | Example | Order |
|-------|---------|-------|
| `ordering` | `?ordering=created_at` | Ascending |
| `ordering` | `?ordering=-priority` | Descending |

Supported fields: `created_at`, `due_at`, `priority`, `updated_at`, `escalation_level`.

**Default sort order**: urgent first → overdue first → newest first.

## Compact Mobile Serializers

### CompactTaskSerializer (list)

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | |
| `title` | string | |
| `status` | string | |
| `priority` | string | |
| `task_type` | string | |
| `due_at` | datetime | ISO8601 |
| `escalation_level` | int | from SLA |
| `sla_breached` | bool | from SLA |
| `created_at` | datetime | ISO8601 |

### CompactTaskDetailSerializer (detail)

Adds: `description`, `assignee_id`, `started_at`, `completed_at`, `notes_count`, `latest_event`, `sla` (nested CompactSLASerializer).

## Throttling

| Scope | Rate | Applies to |
|-------|------|------------|
| `provider_burst` | 60/min | Dashboard API |
| `provider_sustained` | 1000/day | Dashboard API |

Configured in Django settings under ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``.

## Performance Optimizations

- ``select_related("sla")`` — avoids N+1 SLA queries
- ``prefetch_related("events")`` — avoids N+1 event queries
- Compact serializers resolve SLA fields via ``SerializerMethodField`` with
  graceful fallback (no crash if SLA is missing)
- Pagination limits result sets to 100 max

## Realtime Placeholder

`provider_ops/services/realtime_service.py` provides no-op stubs for
future WebSocket/SSE push:

- `publish_task_update(task)` — push task status changes
- `publish_sla_update(task)` — push SLA updates

Full implementation requires:
1. WebSocket or SSE server (Django Channels or similar)
2. Client subscription management
3. Auth integration with mobile token flow

## OpenAPI / drf-spectacular

Endpoint descriptions include query parameter documentation.  Future work:
add ``@extend_schema`` decorators for richer response examples.

## Files

| File | Purpose |
|------|---------|
| `api/pagination.py` | LimitOffsetPagination config |
| `api/filters/task_filters.py` | Query-param based filtering |
| `api/serializers/mobile.py` | CompactTaskSerializer, CompactTaskDetailSerializer, CompactSLASerializer |
| `api/mobile_response.py` | Standardized list response helper |
| `api/throttling.py` | ProviderBurstThrottle, ProviderSustainedThrottle |
| `api/views/task.py` | Updated with pagination/filtering/sorting |
| `api/views/sla.py` | Updated with pagination |
| `api/urls.py` | Versioned paths (`v1/`) |
| `services/realtime_service.py` | Placeholder push service |
