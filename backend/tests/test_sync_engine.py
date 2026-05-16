"""Phase 9B — Owner Canonical Sync Engine tests.

Uses mock objects to avoid database access, reusing the same FakeModel
pattern established by Phase 8 sync checkpoint tests.
"""

from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import sentinel

import pytest
from django.utils import timezone

from apps.integrations.domain.enums import (
    EngagementStatus,
    OutboxStatus,
    SyncItemStatus,
    SyncRunStatus,
    SyncRunType,
)
from apps.integrations.services import sync_engine_service
from apps.integrations.services.engagement_service import EngagementSyncNotAllowed
from apps.integrations.services.sync_engine_service import (
    SyncEngineError,
    SyncEngineEventError,
)
from apps.integrations.services.sync_service import SyncNotAllowed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DoesNotExist(Exception):
    """Fake DoesNotExist for mock model lookups."""


class FakeCheckpointModel:
    DoesNotExist = _DoesNotExist


class FakeSyncRunModel:
    pass


class FakeSyncItemModel:
    pass


class FakeOutboxEventModel:
    DoesNotExist = _DoesNotExist


class FakeEngagement:
    def __init__(self, status=EngagementStatus.ACTIVE, owner_tenant_id="owner-1", provider_tenant_id="provider-1"):
        self.status = status
        self.owner_tenant_id = owner_tenant_id
        self.provider_tenant_id = provider_tenant_id
        self.pk = 1

    def __repr__(self):
        return f"FakeEngagement({self.status})"


class FakeSyncRun:
    def __init__(self, engagement, run_type=SyncRunType.DELTA, status=SyncRunStatus.RUNNING):
        self.engagement = engagement
        self.run_type = run_type
        self.status = status
        self.pk = 1
        self.completed_at = None
        self.failed_at = None
        self.error = ""
        self.stats = None

    def __repr__(self):
        return f"FakeSyncRun({self.status})"


class FakeOutboxEvent:
    def __init__(self, event_id="evt-1", event_type="location.created", aggregate_type="Location",
                 aggregate_id="loc-1", created_at=None, status=OutboxStatus.PROCESSED,
                 target_provider_schema="provider-1"):
        self.event_id = event_id
        self.event_type = event_type
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        self.created_at = created_at or timezone.now()
        self.status = status
        self.target_provider_schema = target_provider_schema


def _patch_engine(monkeypatch):
    """Patch all sync engine dependencies with fake equivalents."""
    fake_events = []

    def _mock_events_iter(**kwargs):
        return iter(fake_events)

    monkeypatch.setattr("django.db.transaction.atomic", lambda: nullcontext())
    monkeypatch.setattr(
        sync_engine_service, "assert_engagement_allows_sync",
        lambda *, engagement: None if engagement.status == EngagementStatus.ACTIVE
        else (_ for _ in ()).throw(EngagementSyncNotAllowed("not active")),
    )

    def _mock_start(engagement, run_type=SyncRunType.DELTA):
        return FakeSyncRun(engagement, run_type)

    def _mock_complete(sync_run, stats=None):
        sync_run.status = SyncRunStatus.COMPLETED
        sync_run.completed_at = timezone.now()
        sync_run.stats = stats
        return sync_run

    def _mock_fail(sync_run, error):
        sync_run.status = SyncRunStatus.FAILED
        sync_run.failed_at = timezone.now()
        sync_run.error = error
        return sync_run

    def _mock_record(sync_run, event_id, event_type, aggregate_type, aggregate_id, status=SyncItemStatus.PENDING, error=""):
        return None

    def _mock_update_checkpoint(engagement, stream_name, event_id, event_created_at, sync_run=None):
        return None

    def _mock_get_checkpoint(engagement, stream_name):
        return None

    monkeypatch.setattr(sync_engine_service, "start_sync_run", _mock_start)
    monkeypatch.setattr(sync_engine_service, "complete_sync_run", _mock_complete)
    monkeypatch.setattr(sync_engine_service, "fail_sync_run", _mock_fail)
    monkeypatch.setattr(sync_engine_service, "record_sync_item", _mock_record)
    monkeypatch.setattr(sync_engine_service, "update_checkpoint", _mock_update_checkpoint)
    monkeypatch.setattr(sync_engine_service, "get_checkpoint", _mock_get_checkpoint)

    return fake_events


def _make_event(**overrides):
    kwargs = dict(
        event_id="evt-1",
        event_type="location.created",
        aggregate_type="Location",
        aggregate_id="loc-1",
        created_at=timezone.now(),
        status=OutboxStatus.PROCESSED,
        target_provider_schema="provider-1",
    )
    kwargs.update(overrides)
    return FakeOutboxEvent(**kwargs)


# ---------------------------------------------------------------------------
# Tests: run_full_sync
# ---------------------------------------------------------------------------


def test_full_sync_creates_run_and_processes_all_streams(monkeypatch):
    eng = FakeEngagement()
    captured_streams = []

    def _mock_process(engagement, stream_name, events, sync_run):
        captured_streams.append(stream_name)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "_execute_sync_run", _mock_process)

    result = sync_engine_service.run_full_sync(engagement=eng)

    assert captured_streams
    assert result.status == SyncRunStatus.COMPLETED


def test_full_sync_passes_correct_run_type(monkeypatch):
    eng = FakeEngagement()
    captured = []

    def _mock_start(engagement, run_type=SyncRunType.DELTA):
        captured.append(run_type)
        return FakeSyncRun(engagement, run_type)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "start_sync_run", _mock_start)
    monkeypatch.setattr(sync_engine_service, "_execute_sync_run", lambda sync_run, engagement: sync_run)

    sync_engine_service.run_full_sync(engagement=eng)

    assert captured == [SyncRunType.FULL]


def test_full_sync_cancelled_on_sync_not_allowed(monkeypatch):
    eng = FakeEngagement(status=EngagementStatus.PENDING)
    cancelled = []

    def _mock_cancel(sync_run, reason=""):
        cancelled.append(reason)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "cancel_sync_run", _mock_cancel)

    with pytest.raises(SyncNotAllowed):
        sync_engine_service.run_full_sync(engagement=eng)

    assert cancelled


def test_full_sync_fails_on_unexpected_error(monkeypatch):
    eng = FakeEngagement()
    failed = []

    def _mock_fail(sync_run, error):
        failed.append(error)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "_execute_sync_run", lambda sync_run, engagement: (_ for _ in ()).throw(ValueError("boom")))
    monkeypatch.setattr(sync_engine_service, "fail_sync_run", _mock_fail)

    with pytest.raises(SyncEngineError):
        sync_engine_service.run_full_sync(engagement=eng)

    assert failed


# ---------------------------------------------------------------------------
# Tests: run_delta_sync
# ---------------------------------------------------------------------------


def test_delta_sync_creates_run_with_delta_type(monkeypatch):
    eng = FakeEngagement()
    captured = []

    def _mock_start(engagement, run_type=SyncRunType.DELTA):
        captured.append(run_type)
        return FakeSyncRun(engagement, run_type)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "start_sync_run", _mock_start)
    monkeypatch.setattr(sync_engine_service, "_execute_sync_run", lambda sync_run, engagement: sync_run)

    sync_engine_service.run_delta_sync(engagement=eng)

    assert captured == [SyncRunType.DELTA]


def test_delta_sync_processes_streams(monkeypatch):
    eng = FakeEngagement()
    captured_streams = []

    def _mock_process(engagement, stream_name, events, sync_run):
        captured_streams.append(stream_name)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "_execute_sync_run", _mock_process)

    result = sync_engine_service.run_delta_sync(engagement=eng)

    assert captured_streams
    assert result.status == SyncRunStatus.COMPLETED


# ---------------------------------------------------------------------------
# Tests: run_resync
# ---------------------------------------------------------------------------


def test_resync_uses_full_run_type(monkeypatch):
    eng = FakeEngagement()
    captured = []

    def _mock_start(engagement, run_type=SyncRunType.DELTA):
        captured.append(run_type)
        return FakeSyncRun(engagement, run_type)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "start_sync_run", _mock_start)
    monkeypatch.setattr(sync_engine_service, "_execute_sync_run", lambda sync_run, engagement: sync_run)

    sync_engine_service.run_resync(engagement=eng, stream_name="locations")

    assert captured == [SyncRunType.RESYNC]


def test_resync_cancelled_on_sync_not_allowed(monkeypatch):
    eng = FakeEngagement(status=EngagementStatus.SUSPENDED)
    cancelled = []

    def _mock_cancel(sync_run, reason=""):
        cancelled.append(reason)

    _patch_engine(monkeypatch)
    monkeypatch.setattr(sync_engine_service, "cancel_sync_run", _mock_cancel)

    with pytest.raises(SyncNotAllowed):
        sync_engine_service.run_resync(engagement=eng, stream_name="locations")

    assert cancelled


# ---------------------------------------------------------------------------
# Tests: _resolve_streams
# ---------------------------------------------------------------------------


def test_resolve_streams_returns_expected_mapping():
    """_resolve_streams returns the correct aggregate-to-stream mapping."""
    from apps.integrations.services.sync_engine_service import _resolve_streams
    streams = _resolve_streams(run_type=SyncRunType.FULL, engagement=FakeEngagement())
    expected_streams = {
        "locations": "Location",
        "devices": "Device",
        "telemetry": "SensorReading",
    }
    assert streams == expected_streams


def test_agg_to_stream_mapping():
    """The AGGREGATE_TO_STREAM module-level constant covers expected types."""
    from apps.integrations.services.sync_engine_service import AGGREGATE_TO_STREAM, STREAM_AGGREGATES
    assert AGGREGATE_TO_STREAM == {
        "Location": "locations",
        "Device": "devices",
        "SensorReading": "telemetry",
    }
    assert STREAM_AGGREGATES == {v: k for k, v in AGGREGATE_TO_STREAM.items()}
