"""Standard API response metadata block.

Attached to all mobile/dashboard list and detail responses.
"""

from django.utils import timezone


def build_meta(request, *, extra: dict | None = None) -> dict:
    """Build the standard ``meta`` block for API responses."""
    rid = getattr(request, "request_id", "")
    cid = getattr(request, "correlation_id", "")
    meta = {
        "request_id": rid,
        "correlation_id": cid,
        "api_version": "v1",
        "generated_at": timezone.now().isoformat(),
    }
    if extra:
        meta.update(extra)
    return meta
