"""Unit tests for the sync engine orchestration (Phase 9B)."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.integrations.domain.enums import (
    EngagementStatus,
    OutboxStatus,
    SyncItemStatus,
    SyncRunStatus,
    SyncRunType,
)
from apps.integrations.services.sync_engine_service import (
    SyncEngineEventError,
    _deliver_and_record,
    _execute_sync_run,
    _is_full_sync,
    _process_stream,
    _record_failed_item,
    _record_processed_item,
    _resolve_streams,
    _transition_to_running,
    run_delta_sync,
    run_full_sync,
    run_resync,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    # transaction.atomic is mocked at the django.db level since
    # sync_engine_service delegates to sync_service which uses it.
    monkeypatch.setattr(
        "django.db.transaction.atomic",
        lambda: nullcontext(),
    )


def _mock_start_sync_run(monkeypatch, run_type=SyncRunType.FULL):
    fake_run = SimpleNamespace(
        pk=1,
        run_type=run_type,
        status=SyncRunStatus.PENDING,
        started_at=timezone.now(),
        engagement=SimpleNamespace(pk=1),
        sync_items=SimpleNamespace(
            count=MagicMock(return_value=10),
            filter=MagicMock(return_value=SimpleNamespace(
                count=MagicMock(return_value=0)
            )),
        ),
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.start_sync_run",
        lambda **kwargs: fake_run,
    )
    return fake_run


def _make_engagement(status=EngagementStatus.ACTIVE, **kw):
    return SimpleNamespace(
        status=status,
        owner_tenant_id=kw.get("owner_tenant_id", "owner-1"),
        provider_tenant_id=kw.get("provider_tenant_id", "provider-1"),
        pk=kw.get("pk", 1),
        _state=SimpleNamespace(db="default"),
        **kw,
    )


def _make_event(**kw):
    return SimpleNamespace(
        pk=kw.get("pk", 1),
        event_id=kw.get("event_id", "evt-1"),
        event_type=kw.get("event_type", "location.created"),
        aggregate_type=kw.get("aggregate_type", "Location"),
        aggregate_id=kw.get("aggregate_id", "loc-1"),
        status=kw.get("status", OutboxStatus.PROCESSED),
        created_at=kw.get("created_at", timezone.now()),
        last_error=kw.get("last_error", ""),
        __class__=SimpleNamespace(__name__="IntegrationOutbox"),
    )


# ============================================================================
# _is_full_sync
# ============================================================================


def test_full_run_is_full_sync():
    run = SimpleNamespace(run_type=SyncRunType.FULL)
    assert _is_full_sync(run) is True


def test_resync_run_is_full_sync():
    run = SimpleNamespace(run_type=SyncRunType.RESYNC)
    assert _is_full_sync(run) is True


def test_delta_run_is_not_full_sync():
    run = SimpleNamespace(run_type=SyncRunType.DELTA)
    assert _is_full_sync(run) is False


# ============================================================================
# _transition_to_running
# ============================================================================


def test_transition_to_running(monkeypatch):
    fake = MagicMock()
    fake.status = SyncRunStatus.PENDING
    _transition_to_running(fake)
    assert fake.status == SyncRunStatus.RUNNING
    fake.save.assert_called_once_with(update_fields=["status"])


# ============================================================================
# _resolve_streams
# ============================================================================


def test_resolve_streams_full_returns_all():
    eng = _make_engagement()
    streams = _resolve_streams(SyncRunType.FULL, eng)
    assert len(streams) == 3
    assert ("locations", "Location") in streams
    assert ("devices", "Device") in streams
    assert ("telemetry", "SensorReading") in streams


def test_resolve_streams_delta_returns_matching(monkeypatch):
    eng = _make_engagement()
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.get_checkpoint",
        lambda **kwargs: None,
    )

    # Mock outbox query for Location aggregate
    class FakeQS:
        def filter(self, **kw):
            return self

        def exists(self):
            return True

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.IntegrationOutbox",
        SimpleNamespace(objects=FakeQS()),
    )

    streams = _resolve_streams(SyncRunType.DELTA, eng)
    assert len(streams) == 3  # All have events


# ============================================================================
# _record_processed_item / _record_failed_item
# ============================================================================


def test_record_processed_item(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    event = _make_event()

    fake_item = SimpleNamespace(pk=1, status=SyncItemStatus.PROCESSED)
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.record_sync_item",
        lambda **kw: fake_item,
    )

    result = _record_processed_item(sync_run=fake_run, event=event)
    assert result.status == SyncItemStatus.PROCESSED


def test_record_failed_item(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    event = _make_event()

    fake_item = SimpleNamespace(pk=2, status=SyncItemStatus.FAILED)
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.record_sync_item",
        lambda **kw: fake_item,
    )

    result = _record_failed_item(sync_run=fake_run, event=event, error="timeout")
    assert result.status == SyncItemStatus.FAILED


# ============================================================================
# _deliver_and_record
# ============================================================================


def test_deliver_and_record_success(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    event = _make_event()

    # Mock deliver_outbox_event to return a "processed" event
    processed_event = SimpleNamespace(status=OutboxStatus.PROCESSED, last_error="")
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.deliver_outbox_event",
        lambda event: processed_event,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._record_processed_item",
        lambda **kw: SimpleNamespace(pk=1, status=SyncItemStatus.PROCESSED),
    )

    # Should not raise
    _deliver_and_record(sync_run=fake_run, event=event, stream_name="locations")


def test_deliver_and_record_failure(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    event = _make_event()

    # Mock deliver_outbox_event to return a "dead_letter" event
    failed_event = SimpleNamespace(
        status=OutboxStatus.DEAD_LETTER,
        last_error="Connection refused",
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.deliver_outbox_event",
        lambda event: failed_event,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._record_failed_item",
        lambda **kw: SimpleNamespace(pk=2, status=SyncItemStatus.FAILED),
    )

    with pytest.raises(SyncEngineEventError):
        _deliver_and_record(sync_run=fake_run, event=event, stream_name="locations")


# ============================================================================
# _process_stream
# ============================================================================


def test_process_stream_processes_events(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    eng = _make_engagement()
    now = timezone.now()
    event = _make_event(created_at=now)

    events_processed = []

    def fake_deliver(**kw):
        events_processed.append(kw.get("event"))
        return None

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._deliver_and_record",
        fake_deliver,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._is_full_sync",
        lambda run: True,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.get_checkpoint",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.update_checkpoint",
        lambda **kwargs: None,
    )

    class FakeQuerySet:
        def filter(self, **kw):
            return self

        def order_by(self, *args):
            return self

        def iterator(self, chunk_size=100):
            return iter([event])

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.IntegrationOutbox",
        SimpleNamespace(objects=FakeQuerySet()),
    )

    _process_stream(
        sync_run=fake_run,
        engagement=eng,
        stream_name="locations",
        aggregate_type="Location",
        checkpoint=None,
    )

    assert len(events_processed) == 1
    assert events_processed[0].event_id == "evt-1"


# ============================================================================
# run_full_sync
# ============================================================================


def test_run_full_sync_creates_and_executes(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = _mock_start_sync_run(monkeypatch, SyncRunType.FULL)
    eng = _make_engagement()

    executed = []

    def fake_execute(**kw):
        executed.append(kw)

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._execute_sync_run",
        fake_execute,
    )

    result = run_full_sync(engagement=eng)
    assert result is fake_run
    assert len(executed) == 1
    assert executed[0]["sync_run"] is fake_run
    assert executed[0]["engagement"] is eng


def test_run_full_sync_active_engagement(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement(EngagementStatus.ACTIVE)
    fake_run = _mock_start_sync_run(monkeypatch, SyncRunType.FULL)
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._execute_sync_run",
        lambda **kw: None,
    )

    result = run_full_sync(engagement=eng)
    assert result is fake_run


# ============================================================================
# run_delta_sync
# ============================================================================


def test_run_delta_sync_creates_delta_run(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement(EngagementStatus.ACTIVE)
    fake_run = _mock_start_sync_run(monkeypatch, SyncRunType.DELTA)
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._execute_sync_run",
        lambda **kw: None,
    )

    result = run_delta_sync(engagement=eng)
    assert result is fake_run
    assert result.run_type == SyncRunType.DELTA


# ============================================================================
# run_resync
# ============================================================================


def test_run_resync_deletes_checkpoint(monkeypatch):
    _mock_atomic(monkeypatch)
    eng = _make_engagement(EngagementStatus.ACTIVE)
    fake_run = _mock_start_sync_run(monkeypatch, SyncRunType.RESYNC)

    deleted = []

    class FakeCheckpointQS:
        def filter(self, **kw):
            return self

        def delete(self):
            deleted.append(True)
            return (1, None)

    # SyncCheckpoint is imported lazily inside run_resync, so we mock
    # at the models path instead.
    monkeypatch.setattr(
        "apps.integrations.models.SyncCheckpoint.objects.filter",
        lambda **kw: FakeCheckpointQS(),
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._execute_sync_run",
        lambda **kw: None,
    )

    result = run_resync(engagement=eng, stream_name="locations")
    assert result is fake_run
    assert len(deleted) == 1


# ============================================================================
# _execute_sync_run — error handling
# ============================================================================


def test_execute_sync_run_completes(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    eng = _make_engagement()

    completed = []

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._transition_to_running",
        lambda run: None,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._resolve_streams",
        lambda *a, **kw: [],
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.complete_sync_run",
        lambda **kw: completed.append(kw),
    )

    _execute_sync_run(sync_run=fake_run, engagement=eng)
    assert len(completed) == 1
    assert "stats" in completed[0]


def test_execute_sync_run_cancels_on_sync_not_allowed(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    eng = _make_engagement()

    cancelled = []

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._transition_to_running",
        lambda run: None,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._resolve_streams",
        MagicMock(side_effect=__import__("apps.integrations.services.sync_service", fromlist=["SyncNotAllowed"]).SyncNotAllowed("no")),
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.cancel_sync_run",
        lambda **kw: cancelled.append(kw),
    )

    _execute_sync_run(sync_run=fake_run, engagement=eng)
    assert len(cancelled) == 1
    assert "Engagement no longer active." in cancelled[0].get("reason", "")


def test_execute_sync_run_fails_on_exception(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_run = MagicMock()
    eng = _make_engagement()

    failed = []

    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._transition_to_running",
        lambda run: None,
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service._resolve_streams",
        MagicMock(side_effect=RuntimeError("unexpected error")),
    )
    monkeypatch.setattr(
        "apps.integrations.services.sync_engine_service.fail_sync_run",
        lambda **kw: failed.append(kw),
    )

    _execute_sync_run(sync_run=fake_run, engagement=eng)
    assert len(failed) == 1
