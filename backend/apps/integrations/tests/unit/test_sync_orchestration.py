"""Unit tests for sync orchestration, locking, health, and management command (Phase 10)."""

from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.integrations.domain.constants import SYNC_RUN_TIMEOUT_SECONDS
from apps.integrations.domain.enums import (
    EngagementStatus,
    SyncRunStatus,
    SyncRunType,
)
from apps.integrations.services.sync_audit import (
    audit_sync_completed,
    audit_sync_failed,
    audit_sync_recovered,
    audit_sync_started,
)
from apps.integrations.services.sync_health_service import (
    EngagementSyncHealth,
    SyncHealthSummary,
    detect_unhealthy_engagements,
    get_metrics_snapshot,
    get_sync_health_summary,
    increment_metric,
    observe_duration,
)
from apps.integrations.services.sync_locking import (
    SyncLockError,
    acquire_sync_lock,
    has_running_sync,
)
from apps.integrations.tasks.sync_tasks import (
    recover_stuck_sync_runs,
    run_delta_sync_task,
    run_full_sync_task,
    run_periodic_delta_syncs,
    run_resync_task,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.transaction.atomic",
        lambda: nullcontext(),
    )


def _make_engagement(status=EngagementStatus.ACTIVE, **kw):
    base = {
        "status": status,
        "owner_tenant_id": "owner-1",
        "provider_tenant_id": "provider-1",
        "pk": 1,
    }
    base.update(kw)
    return SimpleNamespace(**base)


# ============================================================================
# 1. Sync Locking
# ============================================================================


def test_has_running_sync_true(monkeypatch):
    eng = _make_engagement()
    class FakeQS:
        def filter(self, **kw):
            return self
        def exists(self):
            return True
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.SyncRun",
        SimpleNamespace(objects=FakeQS()),
    )
    assert has_running_sync(engagement=eng) is True


def test_has_running_sync_false(monkeypatch):
    eng = _make_engagement()
    class FakeQS:
        def filter(self, **kw):
            return self
        def exists(self):
            return False
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.SyncRun",
        SimpleNamespace(objects=FakeQS()),
    )
    assert has_running_sync(engagement=eng) is False


def test_acquire_sync_lock_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement()
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.ProviderEngagement",
        SimpleNamespace(
            objects=SimpleNamespace(
                select_for_update=MagicMock(
                    return_value=SimpleNamespace(
                        get=MagicMock(return_value=eng)
                    )
                )
            )
        ),
    )
    class FakeQS:
        def filter(self, **kw):
            return self
        def exists(self):
            return False
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.SyncRun",
        SimpleNamespace(objects=FakeQS()),
    )
    acquire_sync_lock(engagement=eng)  # No raise


def test_acquire_sync_lock_raises_when_active(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement()
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.ProviderEngagement",
        SimpleNamespace(
            objects=SimpleNamespace(
                select_for_update=MagicMock(
                    return_value=SimpleNamespace(
                        get=MagicMock(return_value=eng)
                    )
                )
            )
        ),
    )
    class FakeQS:
        def filter(self, **kw):
            return self
        def exists(self):
            return True
    monkeypatch.setattr(
        "apps.integrations.services.sync_locking.SyncRun",
        SimpleNamespace(objects=FakeQS()),
    )
    with pytest.raises(SyncLockError):
        acquire_sync_lock(engagement=eng)


# ============================================================================
# 2. Sync Health
# ============================================================================


def test_sync_health_summary(monkeypatch):
    class FakeCountQS:
        def filter(self, **kw):
            return self
        def count(self):
            return 3
        def __iter__(self):
            return iter([])

    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.ProviderEngagement.objects",
        FakeCountQS(),
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.ProviderEngagement",
        SimpleNamespace(
            objects=FakeCountQS(),
            status=SimpleNamespace(ACTIVE="active", __name__="EngagementStatus"),
        ),
    )

    class FakeRunQS:
        def filter(self, **kw):
            return self
        def count(self):
            return 2
    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.SyncRun",
        SimpleNamespace(objects=FakeRunQS()),
    )

    class FakeOutboxQS:
        def filter(self, **kw):
            return self
        def count(self):
            return 3
    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.IntegrationOutbox",
        SimpleNamespace(objects=FakeOutboxQS()),
    )

    summary = get_sync_health_summary()
    assert isinstance(summary, SyncHealthSummary)
    assert summary.running_sync_count == 2


def test_detect_unhealthy_engagements(monkeypatch):
    fake_eng = _make_engagement(
        pk=1,
        owner_tenant_id="o1",
        provider_tenant_id="p1",
    )

    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.ProviderEngagement.objects",
        SimpleNamespace(
            filter=MagicMock(
                return_value=type("QS", (), {"__iter__": lambda s: iter([fake_eng])})()
            )
        ),
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.ProviderEngagement",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=[fake_eng])
            ),
            status=SimpleNamespace(ACTIVE="active"),
        ),
    )

    monkeypatch.setattr(
        "apps.integrations.services.sync_health_service.get_engagement_sync_health",
        lambda **kw: EngagementSyncHealth(
            engagement_id=1,
            owner_tenant_id="o1",
            provider_tenant_id="p1",
            engagement_status="active",
            overall_healthy=False,
        ),
    )

    unhealthy = detect_unhealthy_engagements()
    assert len(unhealthy) >= 1


def test_metrics_snapshot():
    increment_metric("runs_total", 5)
    increment_metric("runs_failed_total", 1)
    observe_duration(30.0)
    snap = get_metrics_snapshot()
    assert snap.get("runs_total") == 5
    assert snap.get("runs_failed_total") == 1


# ============================================================================
# 3. Audit
# ============================================================================


def test_audit_sync_started(monkeypatch):
    logged = []
    monkeypatch.setattr(
        "apps.integrations.services.sync_audit.AuditLog",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(side_effect=lambda **kw: logged.append(kw))
            )
        ),
    )
    audit_sync_started(engagement_id=1, run_id=42, run_type="delta")
    assert len(logged) == 1
    assert logged[0]["target_type"] == "SyncRun"
    assert logged[0]["target_id"] == "42"


def test_audit_sync_failed(monkeypatch):
    logged = []
    monkeypatch.setattr(
        "apps.integrations.services.sync_audit.AuditLog",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(side_effect=lambda **kw: logged.append(kw))
            )
        ),
    )
    audit_sync_failed(engagement_id=1, run_id=43, error="timeout")
    assert len(logged) == 1


def test_audit_sync_recovered(monkeypatch):
    logged = []
    monkeypatch.setattr(
        "apps.integrations.services.sync_audit.AuditLog",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(side_effect=lambda **kw: logged.append(kw))
            )
        ),
    )
    audit_sync_recovered(run_id=44, error="stuck")
    assert len(logged) == 1


def test_audit_does_not_crash(monkeypatch):
    monkeypatch.setattr(
        "apps.integrations.services.sync_audit.AuditLog",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(side_effect=RuntimeError("DB down"))
            )
        ),
    )
    audit_sync_started(engagement_id=1, run_id=99, run_type="full")
    audit_sync_completed(engagement_id=1, run_id=99, stats={})
    audit_sync_failed(engagement_id=1, run_id=99, error="err")
    audit_sync_cancelled = __import__("apps.integrations.services.sync_audit", fromlist=["audit_sync_cancelled"]).audit_sync_cancelled
    audit_sync_cancelled(engagement_id=1, run_id=99, reason="manual")
    audit_sync_recovered(run_id=99, error="stuck")
    # No crash


# ============================================================================
# 4. Stuck recovery
# ============================================================================


def test_recover_stuck_sync_runs(monkeypatch):
    now = timezone.now()
    stuck_run = MagicMock()
    stuck_run.pk = 1
    stuck_run.status = SyncRunStatus.RUNNING
    stuck_run.started_at = now - timedelta(seconds=SYNC_RUN_TIMEOUT_SECONDS + 100)
    stuck_run.error = ""
    stuck_run.failed_at = None

    class FakeStuckQS:
        def filter(self, **kw):
            return self
        def __iter__(self):
            return iter([stuck_run])

    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.SyncRun",
        SimpleNamespace(objects=FakeStuckQS()),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.transaction.atomic",
        lambda: nullcontext(),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_recovered",
        lambda **kw: None,
    )

    count = recover_stuck_sync_runs()
    assert count == 1
    assert stuck_run.status == SyncRunStatus.FAILED
    assert stuck_run.error == "sync_run_timeout"


# ============================================================================
# 5. Periodic delta sync
# ============================================================================


def test_periodic_delta_sync_skips_running(monkeypatch):
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.ProviderEngagement",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=[
                    _make_engagement(pk=1),
                    _make_engagement(pk=2),
                ])
            )
        ),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.has_running_sync",
        lambda **kw: True,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.run_delta_sync_task",
        MagicMock(delay=MagicMock()),
    )

    result = run_periodic_delta_syncs()
    assert result["skipped_running"] == 2
    assert result["attempted"] == 0


def test_periodic_delta_sync_attempts(monkeypatch):
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.ProviderEngagement",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=[
                    _make_engagement(pk=1),
                ])
            )
        ),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.has_running_sync",
        lambda **kw: False,
    )

    delay_calls = []
    class FakeTask:
        @staticmethod
        def delay(**kw):
            delay_calls.append(kw)

    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.run_delta_sync_task",
        FakeTask,
    )

    result = run_periodic_delta_syncs()
    assert result["attempted"] == 1
    assert len(delay_calls) == 1


# ============================================================================
# 6. Celery tasks
# ============================================================================


def test_delta_sync_task_executes(monkeypatch):
    eng = _make_engagement(pk=1)
    sync_run = SimpleNamespace(
        pk=42,
        run_type=SyncRunType.DELTA,
        status=SyncRunStatus.COMPLETED,
        stats={"processed": 5},
        error="",
    )

    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.ProviderEngagement",
        SimpleNamespace(objects=SimpleNamespace(get=MagicMock(return_value=eng))),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.acquire_sync_lock",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.run_delta_sync",
        lambda **kw: sync_run,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_started",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_completed",
        lambda **kw: None,
    )

    result = run_delta_sync_task(engagement_id=1)
    assert result["sync_run_id"] == 42
    assert result["status"] == SyncRunStatus.COMPLETED


def test_full_sync_task_executes(monkeypatch):
    eng = _make_engagement(pk=2)
    sync_run = SimpleNamespace(
        pk=43, run_type=SyncRunType.FULL,
        status=SyncRunStatus.COMPLETED, stats={}, error="",
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.ProviderEngagement",
        SimpleNamespace(objects=SimpleNamespace(get=MagicMock(return_value=eng))),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.acquire_sync_lock",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.run_full_sync",
        lambda **kw: sync_run,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_started",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_completed",
        lambda **kw: None,
    )

    result = run_full_sync_task(engagement_id=2)
    assert result["status"] == SyncRunStatus.COMPLETED


def test_resync_task_executes(monkeypatch):
    eng = _make_engagement(pk=3)
    sync_run = SimpleNamespace(
        pk=44, run_type=SyncRunType.RESYNC,
        status=SyncRunStatus.COMPLETED, stats={}, error="",
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.ProviderEngagement",
        SimpleNamespace(objects=SimpleNamespace(get=MagicMock(return_value=eng))),
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.acquire_sync_lock",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.run_resync",
        lambda **kw: sync_run,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_started",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.integrations.tasks.sync_tasks.audit_sync_completed",
        lambda **kw: None,
    )

    result = run_resync_task(engagement_id=3, stream_name="locations")
    assert result["status"] == SyncRunStatus.COMPLETED
