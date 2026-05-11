# API Contract Hardening

Phase 16A hardens the provider/mobile API contract for enterprise
production use, without changing any business logic.

## Standardised Error Envelope

Every API error returns this envelope:

```json
{
    "error": {
        "code": "task_invalid_transition",
        "message": "Task cannot transition to the requested status.",
        "details": {},
        "request_id": "abc-123",
        "correlation_id": "def-456",
        "timestamp": "2026-05-11T12:00:00+00:00"
    }
}
```

### Stable Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `task_invalid_transition` | 409 | Invalid task status transition |
| `stale_version` | 409 | Optimistic concurrency conflict |
| `validation_error` | 400 | Field-level validation failures |
| `not_found` | 404 | Resource not found |
| `unauthorized` | 401 | Not authenticated |
| `forbidden` | 403 | Not permitted |
| `throttled` | 429 | Rate limited |
| `conflict` | 409 | General conflict |
| `internal_error` | 500 | Unexpected server error |

## Request ID / Correlation ID

Every request gets:
- **`request_id`**: generated server-side, unique per request
- **`correlation_id`**: read from `X-Correlation-ID` header or generated

IDs are attached to:
- `request.request_id`, `request.correlation_id` (Python)
- `X-Request-ID`, `X-Correlation-ID` response headers
- Error envelope `request_id` / `correlation_id` fields
- Structured log entries

## Optimistic Concurrency

`ProviderTask` and `TaskSLA` support version-based conflict detection:

| Header / Field | Purpose |
|----------------|---------|
| `version` | PositiveIntegerField, auto-incremented on save |
| `If-Match` (future) | HTTP header for version check |
| `X-Version` (response) | Current version in response |

Flow:
1. Client reads resource → gets `version: 5`
2. Client sends update with `version: 5`
3. Server checks: current version matches? → update; conflicts? → 409

## ETag Support

Read responses include `ETag` header computed from `md5(version + updated_at)`.

| Request header | Response |
|----------------|----------|
| `If-None-Match: <etag>` | 304 Not Modified if unchanged |
| No header | Full response with new ETag |

## Structured API Logging

Every API request is logged via `core/logging/api_logger.py`:

| Field | Always? | Example |
|-------|---------|---------|
| request_id | ✅ | `abc-123` |
| correlation_id | ✅ | `def-456` |
| method | ✅ | `GET` |
| path | ✅ | `/api/provider/v1/tasks/` |
| status_code | ✅ | `200` |
| tenant_schema | ✅ | `provider_1` |
| user_id | ✅ | `42` |
| duration_ms | ✅ | `15.3` |

**Never logged:** auth tokens, push tokens, passwords, HMAC secrets, email bodies.

## API Response Meta Block

All list/detail responses include:

```json
{
    "results": [...],
    "meta": {
        "request_id": "abc-123",
        "correlation_id": "def-456",
        "api_version": "v1",
        "generated_at": "2026-05-11T12:00:00+00:00"
    }
}
```

## Idempotency (Placeholder)

Write endpoints support an optional `Idempotency-Key` header.  The
current implementation is a no-op placeholder.  Future phases will
add Redis/Postgres-backed deduplication.

## Files

| File | Purpose |
|------|---------|
| `core/middleware/request_context.py` | Request ID / Correlation ID middleware |
| `core/logging/api_logger.py` | Structured API logging |
| `provider_ops/domain/error_codes.py` | Stable error code constants |
| `provider_ops/api/errors.py` | DRF exception handler + error envelope |
| `provider_ops/api/exceptions.py` | Custom API exception classes |
| `provider_ops/api/concurrency.py` | Version check + ETag computation |
| `provider_ops/api/response_meta.py` | Standard meta block builder |
