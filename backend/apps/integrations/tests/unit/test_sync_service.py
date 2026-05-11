"""Unit tests for SyncRun, SyncCheckpoint, SyncItem lifecycle (Phase 9A)."""

from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.integrations.domain.enums import (
    EngagementStatus,
    SyncItemStatus,
    SyncRunStatus,
    SyncRunType,
)
from apps.integrations.services.engagement_service import (
    EngagementSyncNotAllowed,
    assert_engagement_allows_sync,
)
from apps.integrations.services.sync_service import (
    InvalidSyncRunTransition,
    SyncNotAllowed,
    _validate_sync_run_transition,
    cancel_sync_run,
    complete_sync_run,
    fail_sync_run,
    get_checkpoint,
    record_sync_item,
    start_sync_run,
    update_checkpoint,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.integrations.services.sync_service.transaction.atomic",
        lambda: nullcontext(),
    )


def _make_engagement(status=EngagementStatus.ACTIVE, **kw):
    return SimpleNamespace(
        status=status,
        owner_tenant_id=kw.get("owner_tenant_id", "owner-1"),
        provider_tenant_id=kw.get("provider_tenant_id", "provider-1"),
        pk=kw.get("pk", 1),
        _state=SimpleNamespace(db="default"),
        **kw,
    )


# ============================================================================
# assert_engagement_allows_sync
# ============================================================================


def test_active_engagement_allows_sync():
    eng = _make_engagement(EngagementStatus.ACTIVE)
    assert_engagement_allows_sync(engagement=eng)  # no raise


def test_pending_engagement_blocks_sync():
    eng = _make_engagement(EngagementStatus.PENDING)
    with pytest.raises(EngagementSyncNotAllowed):
        assert_engagement_allows_sync(engagement=eng)


def test_suspended_engagement_blocks_sync():
    eng = _make_engagement(EngagementStatus.SUSPENDED)
    with pytest.raises(EngagementSyncNotAllowed):
        assert_engagement_allows_sync(engagement=eng)


def test_revoked_engagement_blocks_sync():
    eng = _make_engagement(EngagementStatus.REVOKED)
    with pytest.raises(EngagementSyncNotAllowed):
        assert_engagement_allows_sync(engagement=eng)


# ============================================================================
# SyncRun status transitions
# ============================================================================


def test_pending_to_running_allowed():
    _validate_sync_run_transition(SyncRunStatus.PENDING, SyncRunStatus.RUNNING)  # no raise


def test_pending_to_cancelled_allowed():
    _validate_sync_run_transition(SyncRunStatus.PENDING, SyncRunStatus.CANCELLED)  # no raise


def test_running_to_completed_allowed():
    _validate_sync_run_transition(SyncRunStatus.RUNNING, SyncRunStatus.COMPLETED)  # no raise


def test_running_to_failed_allowed():
    _validate_sync_run_transition(SyncRunStatus.RUNNING, SyncRunStatus.FAILED)  # no raise


def test_running_to_cancelled_allowed():
    _validate_sync_run_transition(SyncRunStatus.RUNNING, SyncRunStatus.CANCELLED)  # no raise


def test_completed_is_terminal():
    for target in SyncRunStatus.values:
        if target == SyncRunStatus.COMPLETED:
            continue
        with pytest.raises(InvalidSyncRunTransition):
            _validate_sync_run_transition(SyncRunStatus.COMPLETED, target)


def test_failed_is_terminal():
    for target in SyncRunStatus.values:
        if target == SyncRunStatus.FAILED:
            continue
        with pytest.raises(InvalidSyncRunTransition):
            _validate_sync_run_transition(SyncRunStatus.FAILED, target)


def test_cancelled_is_terminal():
    for target in SyncRunStatus.values:
        if target == SyncRunStatus.CANCELLED:
            continue
        with pytest.raises(InvalidSyncRunTransition):
            _validate_sync_run_transition(SyncRunStatus.CANCELLED, target)


def test_pending_to_failed_denied():
    with pytest.raises(InvalidSyncRunTransition):
        _validate_sync_run_transition(SyncRunStatus.PENDING, SyncRunStatus.FAILED)


def test_pending_to_completed_denied():
    with pytest.raises(InvalidSyncRunTransition):
        _validate_sync_run_transition(SyncRunStatus.PENDING, SyncRunStatus.COMPLETED)


# ============================================================================
# start_sync_run
# ============================================================================


def test_start_sync_run_creates_pending(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.integrations.services.sync_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    eng = _make_engagement(EngagementStatus.ACTIVE)

    class FakeSyncRun:
        objects = SimpleNamespace(
            create=MagicMock(
                return_value=SimpleNamespace(
                    engagement=eng,
                    run_type=SyncRunType.DELTA,
                    status=SyncRunStatus.PENDING,
                    started_at=now,
                )
            )
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncRun",
        FakeSyncRun,
    )

    result = start_sync_run(engagement=eng, run_type=SyncRunType.DELTA)
    assert result.status == SyncRunStatus.PENDING
    assert result.run_type == SyncRunType.DELTA
    assert result.started_at == now


def test_start_sync_run_pending_engagement_raises(monkeypatch):
    eng = _make_engagement(EngagementStatus.PENDING)
    with pytest.raises(SyncNotAllowed):
        start_sync_run(engagement=eng)


def test_start_sync_run_suspended_engagement_raises(monkeypatch):
    eng = _make_engagement(EngagementStatus.SUSPENDED)
    with pytest.raises(SyncNotAllowed):
        start_sync_run(engagement=eng)


def test_start_sync_run_revoked_engagement_raises(monkeypatch):
    eng = _make_engagement(EngagementStatus.REVOKED)
    with pytest.raises(SyncNotAllowed):
        start_sync_run(engagement=eng)


# ============================================================================
# complete_sync_run
# ============================================================================


def test_complete_sync_run_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.integrations.services.sync_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    fake = MagicMock()
    fake.status = SyncRunStatus.RUNNING

    result = complete_sync_run(sync_run=fake, stats={"processed": 42})
    assert result.status == SyncRunStatus.COMPLETED
    assert result.completed_at == now
    assert result.stats == {"processed": 42}


def test_complete_sync_run_terminal_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = SyncRunStatus.COMPLETED
    with pytest.raises(InvalidSyncRunTransition):
        complete_sync_run(sync_run=fake)


# ============================================================================
# fail_sync_run
# ============================================================================


def test_fail_sync_run_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.integrations.services.sync_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    fake = MagicMock()
    fake.status = SyncRunStatus.RUNNING

    result = fail_sync_run(sync_run=fake, error="Connection lost")
    assert result.status == SyncRunStatus.FAILED
    assert result.failed_at == now
    assert result.error == "Connection lost"


def test_fail_sync_run_terminal_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = SyncRunStatus.FAILED
    with pytest.raises(InvalidSyncRunTransition):
        fail_sync_run(sync_run=fake, error="already failed")


# ============================================================================
# cancel_sync_run
# ============================================================================


def test_cancel_pending_sync_run_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.integrations.services.sync_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    fake = MagicMock()
    fake.status = SyncRunStatus.PENDING

    result = cancel_sync_run(sync_run=fake, reason="Manual abort")
    assert result.status == SyncRunStatus.CANCELLED
    assert result.error == "Manual abort"


def test_cancel_running_sync_run_succeeds(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.integrations.services.sync_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    fake = MagicMock()
    fake.status = SyncRunStatus.RUNNING

    result = cancel_sync_run(sync_run=fake)
    assert result.status == SyncRunStatus.CANCELLED


def test_cancel_completed_sync_run_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = SyncRunStatus.COMPLETED
    with pytest.raises(InvalidSyncRunTransition):
        cancel_sync_run(sync_run=fake)


# ============================================================================
# record_sync_item
# ============================================================================


def test_record_sync_item(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()

    class FakeSyncItem:
        objects = SimpleNamespace(
            create=MagicMock(
                return_value=SimpleNamespace(
                    sync_run=fake_run,
                    event_id="evt-1",
                    event_type="location.created",
                    aggregate_type="Location",
                    aggregate_id="loc-1",
                    status=SyncItemStatus.PENDING,
                )
            )
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncItem",
        FakeSyncItem,
    )

    item = record_sync_item(
        sync_run=fake_run,
        event_id="evt-1",
        event_type="location.created",
        aggregate_type="Location",
        aggregate_id="loc-1",
    )
    assert item.event_id == "evt-1"
    assert item.status == SyncItemStatus.PENDING


# ============================================================================
# update_checkpoint / get_checkpoint
# ============================================================================


def test_checkpoint_created_first_time(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement(EngagementStatus.ACTIVE)
    now = timezone.now()

    class _NotFound(Exception):
        pass

    class FakeCheckpoint:
        DoesNotExist = _NotFound
        objects = SimpleNamespace(
            select_for_update=MagicMock(return_value=SimpleNamespace(
                get=MagicMock(side_effect=_NotFound())
            )),
            create=MagicMock(
                return_value=SimpleNamespace(
                    engagement=eng,
                    stream_name="locations",
                    last_event_id="evt-1",
                    last_event_created_at=now,
                    last_successful_run=None,
                )
            ),
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncCheckpoint",
        FakeCheckpoint,
    )

    result = update_checkpoint(
        engagement=eng,
        stream_name="locations",
        event_id="evt-1",
        event_created_at=now,
    )
    assert result.last_event_id == "evt-1"


def test_checkpoint_update_idempotent_for_same_event(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement(EngagementStatus.ACTIVE)
    now = timezone.now()

    class FakeCheckpoint:
        DoesNotExist = Exception
        objects = SimpleNamespace(
            select_for_update=MagicMock(return_value=SimpleNamespace(
                get=MagicMock(
                    return_value=SimpleNamespace(
                        engagement=eng,
                        stream_name="locations",
                        last_event_id="evt-1",
                        last_event_created_at=now,
                        last_successful_run=None,
                        save=MagicMock(),
                    )
                )
            )),
            create=MagicMock(),
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncCheckpoint",
        FakeCheckpoint,
    )

    # First update with the same timestamp — should not advance
    result = update_checkpoint(
        engagement=eng,
        stream_name="locations",
        event_id="evt-1",
        event_created_at=now,
    )
    # The internal _advance_checkpoint returns False, so no create/save called
    assert result == FakeCheckpoint.objects.select_for_update().get()


def test_checkpoint_does_not_go_backwards(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement(EngagementStatus.ACTIVE)
    now = timezone.now()
    earlier = now - timedelta(hours=1)

    class FakeCheckpoint:
        DoesNotExist = Exception
        objects = SimpleNamespace(
            select_for_update=MagicMock(return_value=SimpleNamespace(
                get=MagicMock(
                    return_value=SimpleNamespace(
                        engagement=eng,
                        stream_name="locations",
                        last_event_id="evt-2",
                        last_event_created_at=now,
                        last_successful_run=None,
                        save=MagicMock(),
                    )
                )
            )),
            create=MagicMock(),
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncCheckpoint",
        FakeCheckpoint,
    )

    # Attempt to update with an older timestamp — should NOT advance
    result = update_checkpoint(
        engagement=eng,
        stream_name="locations",
        event_id="evt-1",
        event_created_at=earlier,
    )
    assert result.last_event_id == "evt-2"
    assert result.last_event_created_at == now


def test_get_checkpoint_exists(monkeypatch):
    eng = _make_engagement(EngagementStatus.ACTIVE)
    fake_cp = SimpleNamespace(
        engagement=eng,
        stream_name="devices",
        last_event_id="evt-5",
        last_event_created_at=timezone.now(),
    )
    class FakeModel:
        class DoesNotExist(Exception):
            pass
        objects = SimpleNamespace(
            get=MagicMock(return_value=fake_cp)
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncCheckpoint",
        FakeModel,
    )

    result = get_checkpoint(engagement=eng, stream_name="devices")
    assert result is not None
    assert result.last_event_id == "evt-5"


def test_get_checkpoint_not_exists(monkeypatch):
    eng = _make_engagement(EngagementStatus.ACTIVE)

    class _NotFound(Exception):
        pass

    class FakeModel:
        DoesNotExist = _NotFound
        objects = SimpleNamespace(
            get=MagicMock(side_effect=_NotFound())
        )

    monkeypatch.setattr(
        "apps.integrations.services.sync_service.SyncCheckpoint",
        FakeModel,
    )

    result = get_checkpoint(engagement=eng, stream_name="devices")
    assert result is None
