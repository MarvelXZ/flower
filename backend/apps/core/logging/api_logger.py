"""Structured API request logging.

Logs every API request with stable fields for observability.
Sensitive data is never logged.
"""

import logging

logger = logging.getLogger("flower.api")


def log_api_request(request, response, *, duration_ms: float | None = None) -> None:
    """Log a single API request with structured fields."""
    rid = getattr(request, "request_id", "")
    cid = getattr(request, "correlation_id", "")
    tenant = getattr(request, "tenant", None)
    schema_name = getattr(tenant, "schema_name", "") if tenant else ""
    user = getattr(request, "user", None)

    extra = {
        "request_id": rid,
        "correlation_id": cid,
        "method": request.method,
        "path": request.path,
        "status_code": response.status_code,
        "tenant_schema": schema_name,
        "user_id": getattr(user, "pk", None),
    }
    if duration_ms is not None:
        extra["duration_ms"] = round(duration_ms, 1)

    logger.info("api_request", extra=extra)
