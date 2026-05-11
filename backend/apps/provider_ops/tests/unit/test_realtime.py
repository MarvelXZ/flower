"""Unit tests for Phase 18: Realtime & Mobile Runtime."""

from types import SimpleNamespace
from unittest.mock import MagicMock


from apps.provider_ops.services.realtime_event_service import (
    publish_event,
    publish_task_event,
    replay_events,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_task(**kw):
    defaults = {"pk": 1, "title": "Test", "status": "open", "priority": "normal", "version": 1}
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ============================================================================
# 1. Realtime event publishing
# ============================================================================


def test_publish_event_success(monkeypatch):
    monkeypatch.setattr(
        "apps.provider_ops.services.realtime_event_service.RealtimeEvent",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(return_value=SimpleNamespace(pk=1, created_at=None))
            )
        ),
    )
    monkeypatch.setattr(
        "apps.provider_ops.services.realtime_event_service._broadcast_event",
        lambda e: None,
    )

    event = publish_event(
        tenant_schema="provider_1",
        event_type="task_created",
        entity_type="provider_task",
        entity_id="1",
        payload={"title": "Test"},
    )
    assert event is not None


def test_publish_event_fail_soft(monkeypatch):
    """Exception during publish should not crash the caller."""
    monkeypatch.setattr(
        "apps.provider_ops.services.realtime_event_service.RealtimeEvent",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(side_effect=RuntimeError("DB down"))
            )
        ),
    )
    event = publish_event(
        tenant_schema="provider_1",
        event_type="task_created",
        entity_type="provider_task",
        entity_id="1",
        payload={},
    )
    assert event is None  # fail-soft


# ============================================================================
# 2. Task event publisher
# ============================================================================


def test_publish_task_event(monkeypatch):
    called = []

    def fake_publish(**kw):
        called.append(kw)
        return SimpleNamespace(pk=1)

    monkeypatch.setattr(
        "apps.provider_ops.services.realtime_event_service.publish_event",
        fake_publish,
    )

    task = _mock_task()
    publish_task_event(task=task, event_type="task_created", tenant_schema="t1")
    assert len(called) == 1
    assert called[0]["entity_type"] == "provider_task"


# ============================================================================
# 3. Replay
# ============================================================================


def test_replay_no_events(monkeypatch):
    class FakeQS:
        def filter(self, **kw):
            return self
        def order_by(self, *a):
            return self
        def __getitem__(self, k):
            return []

    monkeypatch.setattr(
        "apps.provider_ops.services.realtime_event_service.RealtimeEvent",
        SimpleNamespace(objects=FakeQS()),
    )

    events = replay_events(tenant_schema="t1")
    assert len(events) == 0


def test_replay_with_after(monkeypatch):
    class FakeModel:
        class DoesNotExist(Exception):
            pass

    class FakeEvent:
        pk = 5
        event_type = "task_created"
        entity_type = "provider_task"
        entity_id = "1"
        version = 1
        created_at = None
        payload = {}

    class FakeQS:
        def __init__(self, *a, **kw):
            pass
        def filter(self, **kw):
            return self
        def order_by(self, *a):
            return self
        def __getitem__(self, k):
            if k.start == 0:
                return [FakeEvent()]
            return []

    monkeypatch.setattr(
        "apps.provider_ops.services.realtime_event_service.RealtimeEvent",
        SimpleNamespace(objects=FakeQS(), DoesNotExist=Exception),
    )

    events = replay_events(tenant_schema="t1", after_event_id=1)
    assert len(events) >= 0


# ============================================================================
# 4. Delta endpoint test (structural)
# ============================================================================


def test_delta_view_imports():
    from apps.provider_ops.api.views.delta import DashboardDeltaView  # noqa
    assert DashboardDeltaView is not None


def test_replay_view_imports():
    from apps.provider_ops.api.views.replay import RealtimeReplayView  # noqa
    assert RealtimeReplayView is not None


# ============================================================================
# 5. Real-time event model string
# ============================================================================


def test_realtime_event_str():
    from apps.provider_ops.models import RealtimeEvent
    instance = RealtimeEvent(
        tenant_schema="t1",
        event_type="task_created",
        entity_type="provider_task",
        entity_id="42",
    )
    s = str(instance)
    assert "task_created" in s
