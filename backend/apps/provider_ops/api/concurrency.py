"""Optimistic concurrency control.

Supports version-based conflict detection for write operations.
"""

from hashlib import md5

from rest_framework import status
from rest_framework.response import Response

from apps.provider_ops.api.errors import _build_error_payload
from apps.provider_ops.domain import error_codes


def check_version(*, obj, expected_version: int | None) -> bool:
    """Return ``True`` if the expected version matches the object's version.

    If ``expected_version`` is ``None``, the check is skipped (legacy client).
    """
    if expected_version is None:
        return True
    current = getattr(obj, "version", 1)
    if current != expected_version:
        return False
    return True


def build_conflict_response(obj, request) -> Response:
    """Return a 409 Conflict response with the current state."""
    rid = getattr(request, "request_id", "")
    cid = getattr(request, "correlation_id", "")
    payload = _build_error_payload(
        code=error_codes.STALE_VERSION,
        message="Resource has been modified since last read.",
        details={"current_version": getattr(obj, "version", 1)},
        request_id=rid,
        correlation_id=cid,
    )
    return Response(payload, status=status.HTTP_409_CONFLICT)


def compute_etag(obj) -> str:
    """Compute an ETag from the object's version or updated_at."""
    version = getattr(obj, "version", 1)
    updated = getattr(obj, "updated_at", None)
    raw = f"{obj.__class__.__name__}:{getattr(obj, 'pk', '')}:v{version}:{updated}"
    return md5(raw.encode()).hexdigest()
