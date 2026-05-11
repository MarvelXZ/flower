import logging

from apps.audit.domain.enums import AuditAction
from apps.audit.models import AuditLog


logger = logging.getLogger(__name__)


SENSITIVE_METADATA_TERMS = ("secret", "api_key", "authorization", "signature")


def _safe_metadata(metadata: dict | None) -> dict:
    cleaned = {}
    for key, value in (metadata or {}).items():
        if any(term in key.lower() for term in SENSITIVE_METADATA_TERMS):
            cleaned[key] = "[redacted]"
        else:
            cleaned[key] = value
    return cleaned


def audit_integration_event(
    *,
    event_type: str,
    target_type: str,
    target_id: str,
    metadata: dict | None = None,
    actor=None,
):
    """Record an integration audit event without breaking the primary flow."""
    safe_metadata = {"event_type": event_type, **_safe_metadata(metadata)}
    try:
        return AuditLog.objects.create(
            actor=actor,
            action=AuditAction.SECURITY,
            target_type=target_type,
            target_id=str(target_id),
            metadata=safe_metadata,
        )
    except Exception:  # pragma: no cover - defensive by design
        logger.warning(
            "integration_audit_event_failed",
            extra={
                "event_type": event_type,
                "target_type": target_type,
                "target_id": str(target_id),
            },
        )
        return None
