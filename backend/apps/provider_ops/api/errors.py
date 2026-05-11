"""Standardized API error envelope and DRF exception handler.

Every API error returns:

{
    "error": {
        "code": "task_invalid_transition",
        "message": "Human-readable description.",
        "details": {},
        "request_id": "...",
        "correlation_id": "...",
        "timestamp": "..."
    }
}
"""

from django.utils import timezone
from rest_framework.exceptions import (
    APIException,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler

from apps.provider_ops.domain import error_codes


def _get_request_ids(request) -> tuple[str, str]:
    """Extract request_id and correlation_id from the request."""
    req = getattr(request, "_request", request)
    return (
        getattr(req, "request_id", ""),
        getattr(req, "correlation_id", ""),
    )


def _build_error_payload(
    code: str,
    message: str,
    details: dict | None = None,
    request_id: str = "",
    correlation_id: str = "",
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": request_id,
            "correlation_id": correlation_id,
            "timestamp": timezone.now().isoformat(),
        }
    }


def _map_exception_to_code(exc: APIException) -> str:
    """Map DRF exception types to stable error codes."""
    mapping = {
        ValidationError: error_codes.VALIDATION_ERROR,
        NotFound: error_codes.NOT_FOUND,
        NotAuthenticated: error_codes.UNAUTHORIZED,
        PermissionDenied: error_codes.FORBIDDEN,
        Throttled: error_codes.THROTTLED,
    }
    for cls, code in mapping.items():
        if isinstance(exc, cls):
            return code
    return error_codes.INTERNAL_ERROR


def flower_exception_handler(exc, context):
    """Custom DRF exception handler that returns a stable error envelope."""
    request = context.get("request")
    rid, cid = _get_request_ids(request)

    # Let DRF handle the response first
    response = exception_handler(exc, context)

    if response is not None:
        code = _map_exception_to_code(exc)
        details = {}
        if isinstance(exc, ValidationError):
            details = response.data if isinstance(response.data, dict) else {"field_errors": response.data}

        message = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        if isinstance(message, (list, dict)):
            message = str(message)

        payload = _build_error_payload(
            code=code,
            message=message,
            details=details,
            request_id=rid,
            correlation_id=cid,
        )

        # Preserve status code for Throttled
        if isinstance(exc, Throttled):
            payload["error"]["retry_after"] = getattr(exc, "wait", None)

        response.data = payload

    return response
