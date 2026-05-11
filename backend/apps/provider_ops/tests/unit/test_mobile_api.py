"""Unit tests for mobile-ready provider dashboard API (Phase 16)."""

from types import SimpleNamespace


from apps.provider_ops.api.filters.task_filters import TaskFilter
from apps.provider_ops.api.pagination import ProviderDashboardPagination


# ============================================================================
# 1. Pagination
# ============================================================================


def test_pagination_default_limit():
    p = ProviderDashboardPagination()
    assert p.default_limit == 20
    assert p.max_limit == 100


# ============================================================================
# 2. TaskFilter
# ============================================================================


def test_filter_by_status(monkeypatch):
    filtered = []

    class FakeQS:
        def filter(self, **kw):
            filtered.append(kw)
            return self

    f = TaskFilter({"status": "open"})
    f.apply(FakeQS())
    assert any("open" in str(v) for v in filtered)


def test_filter_by_priority(monkeypatch):
    filtered = []

    class FakeQS:
        def filter(self, **kw):
            filtered.append(kw)
            return self

    f = TaskFilter({"priority": "urgent"})
    f.apply(FakeQS())
    assert any("urgent" in str(v) for v in filtered)


def test_filter_by_task_type(monkeypatch):
    filtered = []

    class FakeQS:
        def filter(self, **kw):
            filtered.append(kw)
            return self

    f = TaskFilter({"task_type": "watering"})
    f.apply(FakeQS())
    assert any("watering" in str(v) for v in filtered)


def test_filter_by_assignee(monkeypatch):
    filtered = []

    class FakeQS:
        def filter(self, **kw):
            filtered.append(kw)
            return self

    f = TaskFilter({"assignee_id": "worker-1"})
    f.apply(FakeQS())
    assert any("worker-1" in str(v) for v in filtered)


def test_filter_overdue(monkeypatch):
    class FakeQS:
        def filter(self, **kw):
            return self

    f = TaskFilter({"overdue": "true"})
    result = f.apply(FakeQS())
    assert result is not None


def test_filter_breached(monkeypatch):
    class FakeQS:
        def filter(self, *a, **kw):
            return self

    f = TaskFilter({"breached": "true"})
    result = f.apply(FakeQS())
    assert result is not None


# ============================================================================
# 3. Compact serializers — structural tests
# ============================================================================


def test_compact_serializer_has_minimal_fields():
    from apps.provider_ops.api.serializers.mobile import CompactTaskSerializer
    fields = set(CompactTaskSerializer.Meta.fields)
    assert "title" in fields
    assert "status" in fields
    assert "priority" in fields
    # No heavy nested fields
    assert "events" not in fields
    assert "notes" not in fields


def test_compact_detail_serializer_has_sla():
    from apps.provider_ops.api.serializers.mobile import CompactTaskDetailSerializer
    fields = set(CompactTaskDetailSerializer.Meta.fields)
    assert "sla" in fields
    assert "notes_count" in fields
    assert "latest_event" in fields


# ============================================================================
# 4. Realtime service (placeholder)
# ============================================================================


def test_realtime_publish_task_update_noop():
    from apps.provider_ops.services.realtime_service import publish_task_update
    task = SimpleNamespace(pk=1, status="open")
    publish_task_update(task)  # No crash


def test_realtime_publish_sla_update_noop():
    from apps.provider_ops.services.realtime_service import publish_sla_update
    task = SimpleNamespace(pk=1)
    publish_sla_update(task)  # No crash


# ============================================================================
# 5. Throttling (structural)
# ============================================================================


def test_provider_burst_throttle_rate():
    from apps.provider_ops.api.throttling import ProviderBurstThrottle
    t = ProviderBurstThrottle()
    assert t.rate == "60/min"


def test_provider_sustained_throttle_rate():
    from apps.provider_ops.api.throttling import ProviderSustainedThrottle
    t = ProviderSustainedThrottle()
    assert t.rate == "1000/day"


# ============================================================================
# 6. Models __init__.py export check
# ============================================================================


def test_models_import_tasksla():
    from apps.provider_ops.models import TaskSLA  # noqa
    assert TaskSLA is not None


def test_models_import_taskescalation():
    from apps.provider_ops.models import TaskEscalationEvent  # noqa
    assert TaskEscalationEvent is not None
