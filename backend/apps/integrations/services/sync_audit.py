"""Best-effort audit events for sync lifecycle."""

import logging

from apps.audit.domain.enums import AuditAction
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)


def _safe_metadata(metadata: dict | None) -> dict:
    return {k: v for k, v in (metadata or {}).items()}


def _record_audit(*, event_type: str, target_type: str, target_id: str, metadata: dict | None = None):
    try:
        AuditLog.objects.create(
            actor=None,
            action=AuditAction.SYNC,
            target_type=target_type,
            target_id=str(target_id),
            metadata={"sync_event": event_type, **(_safe_metadata(metadata) or {})},
        )
    except Exception:
        logger.warning("sync_audit_failed", extra={"event_type": event_type, "target_id": str(target_id)})


def audit_sync_started(*, engagement_id: int, run_id: int, run_type: str) -> None:
    _record_audit(
        event_type="sync_started",
        target_type="SyncRun",
        target_id=str(run_id),
        metadata={"engagement_id": str(engagement_id), "run_type": run_type},
    )


def audit_sync_completed(*, engagement_id: int, run_id: int, stats: dict | None = None) -> None:
    _record_audit(
        event_type="sync_completed",
        target_type="SyncRun",
        target_id=str(run_id),
        metadata={"engagement_id": str(engagement_id), "stats": stats},
    )


def audit_sync_failed(*, engagement_id: int, run_id: int, error: str) -> None:
    _record_audit(
        event_type="sync_failed",
        target_type="SyncRun",
        target_id=str(run_id),
        metadata={"engagement_id": str(engagement_id), "error": error[:500]},
    )


def audit_sync_cancelled(*, engagement_id: int, run_id: int, reason: str) -> None:
    _record_audit(
        event_type="sync_cancelled",
        target_type="SyncRun",
        target_id=str(run_id),
        metadata={"engagement_id": str(engagement_id), "reason": reason[:500]},
    )


def audit_sync_recovered(*, run_id: int, error: str) -> None:
    _record_audit(
        event_type="sync_recovered",
        target_type="SyncRun",
        target_id=str(run_id),
        metadata={"recovery_error": error[:500]},
    )
