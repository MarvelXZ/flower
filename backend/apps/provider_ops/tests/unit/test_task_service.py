"""Unit tests for provider task workflow (Phase 14)."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from apps.provider_ops.domain.enums import (
    ProviderTaskPriority,
    ProviderTaskStatus,
    ProviderTaskType,
)
from apps.provider_ops.services.alert_task_mapper import (
    build_task_key,
    map_alert_to_task_payload,
)
from apps.provider_ops.services.task_service import (
    InvalidTaskTransition,
    _validate_transition,
    add_task_note,
    assign_task,
    cancel_task,
    complete_task,
    create_task,
    start_task,
)
from apps.provider_ops.selectors.task_selectors import (
    list_open_tasks,
    task_dashboard_summary,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.provider_ops.services.task_service.transaction.atomic",
        lambda: nullcontext(),
    )


def _make_task(status=ProviderTaskStatus.OPEN, **kw):
    defaults = {
        "pk": 1,
        "task_key": "owner-1:alert-1:watering",
        "source_owner_tenant_id": "owner-1",
        "task_type": ProviderTaskType.WATERING,
        "priority": ProviderTaskPriority.NORMAL,
        "status": status,
        "title": "Water plant",
        "assignee_id": "",
        "started_at": None,
        "completed_at": None,
        "cancelled_at": None,
        "save": MagicMock(),
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _patch_event(monkeypatch):
    monkeypatch.setattr(
        "apps.provider_ops.services.task_service.ProviderTaskEvent",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(return_value=SimpleNamespace(pk=1))
            )
        ),
    )


def _patch_note(monkeypatch):
    monkeypatch.setattr(
        "apps.provider_ops.services.task_service.ProviderTaskNote",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(return_value=SimpleNamespace(pk=1))
            )
        ),
    )


# ============================================================================
# 1. Status transitions
# ============================================================================


def test_open_to_assigned_allowed():
    _validate_transition(ProviderTaskStatus.OPEN, ProviderTaskStatus.ASSIGNED)


def test_open_to_in_progress_allowed():
    _validate_transition(ProviderTaskStatus.OPEN, ProviderTaskStatus.IN_PROGRESS)


def test_open_to_cancelled_allowed():
    _validate_transition(ProviderTaskStatus.OPEN, ProviderTaskStatus.CANCELLED)


def test_assigned_to_in_progress_allowed():
    _validate_transition(ProviderTaskStatus.ASSIGNED, ProviderTaskStatus.IN_PROGRESS)


def test_in_progress_to_completed_allowed():
    _validate_transition(ProviderTaskStatus.IN_PROGRESS, ProviderTaskStatus.COMPLETED)


def test_completed_is_terminal():
    for t in (ProviderTaskStatus.OPEN, ProviderTaskStatus.ASSIGNED, ProviderTaskStatus.IN_PROGRESS, ProviderTaskStatus.CANCELLED):
        with pytest.raises(InvalidTaskTransition):
            _validate_transition(ProviderTaskStatus.COMPLETED, t)


def test_cancelled_is_terminal():
    with pytest.raises(InvalidTaskTransition):
        _validate_transition(ProviderTaskStatus.CANCELLED, ProviderTaskStatus.IN_PROGRESS)


def test_open_to_completed_denied():
    with pytest.raises(InvalidTaskTransition):
        _validate_transition(ProviderTaskStatus.OPEN, ProviderTaskStatus.COMPLETED)


# ============================================================================
# 2. create_task
# ============================================================================


def test_create_task_creates(monkeypatch):
    _mock_atomic(monkeypatch)
    _patch_event(monkeypatch)


    returned = {"pk": 1, "status": ProviderTaskStatus.OPEN}
    class FakeTask:
        objects = SimpleNamespace(
            filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=None))),
            create=MagicMock(
                side_effect=lambda **kw: SimpleNamespace(**{**returned, **kw})
            ),
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.task_service.ProviderTask",
        FakeTask,
    )

    task = create_task(
        task_key="test:key",
        source_owner_tenant_id="owner-1",
        task_type=ProviderTaskType.WATERING,
        title="Water plant",
    )
    assert task.task_key == "test:key"
    assert task.status == ProviderTaskStatus.OPEN


def test_create_task_same_key_no_duplicate(monkeypatch):
    _mock_atomic(monkeypatch)
    existing = _make_task(task_key="dup:key")

    class FakeTask:
        objects = SimpleNamespace(
            filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=existing))),
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.task_service.ProviderTask",
        FakeTask,
    )

    task = create_task(task_key="dup:key", source_owner_tenant_id="o1", task_type="watering", title="Dup")
    assert task is existing


# ============================================================================
# 3. assign / start / complete / cancel
# ============================================================================


def test_assign_task(monkeypatch):
    _mock_atomic(monkeypatch)
    _patch_event(monkeypatch)
    task = _make_task(ProviderTaskStatus.OPEN)
    result = assign_task(task=task, assignee_id="worker-1")
    assert result.status == ProviderTaskStatus.ASSIGNED


def test_start_task(monkeypatch):
    _mock_atomic(monkeypatch)
    _patch_event(monkeypatch)
    task = _make_task(ProviderTaskStatus.ASSIGNED)
    result = start_task(task=task)
    assert result.status == ProviderTaskStatus.IN_PROGRESS


def test_complete_task(monkeypatch):
    _mock_atomic(monkeypatch)
    _patch_event(monkeypatch)
    _patch_note(monkeypatch)
    task = _make_task(ProviderTaskStatus.IN_PROGRESS)
    result = complete_task(task=task, completion_note="Done")
    assert result.status == ProviderTaskStatus.COMPLETED


def test_cancel_task(monkeypatch):
    _mock_atomic(monkeypatch)
    _patch_event(monkeypatch)
    task = _make_task(ProviderTaskStatus.OPEN)
    result = cancel_task(task=task, reason="No longer needed")
    assert result.status == ProviderTaskStatus.CANCELLED


def test_completed_terminal_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    task = _make_task(ProviderTaskStatus.COMPLETED)
    with pytest.raises(InvalidTaskTransition):
        assign_task(task=task, assignee_id="x")


# ============================================================================
# 4. add_task_note
# ============================================================================


def test_add_task_note(monkeypatch):
    _mock_atomic(monkeypatch)
    _patch_event(monkeypatch)
    _patch_note(monkeypatch)
    task = _make_task()
    note = add_task_note(task=task, body="Checked the plant")
    assert note is not None


# ============================================================================
# 5. Alert mapping
# ============================================================================


def test_soil_moisture_low_maps_to_watering():
    p = map_alert_to_task_payload(rule_code="soil_moisture_low", severity="critical", title="Low moisture", message="20%")
    assert p.task_type == ProviderTaskType.WATERING


def test_battery_low_maps_to_device_check():
    p = map_alert_to_task_payload(rule_code="battery_low", severity="warning", title="Battery low", message="10%")
    assert p.task_type == ProviderTaskType.DEVICE_CHECK


def test_critical_severity_maps_to_urgent():
    p = map_alert_to_task_payload(rule_code="soil_moisture_low", severity="critical", title="X", message="X")
    assert p.priority == ProviderTaskPriority.URGENT


def test_warning_severity_maps_to_high():
    p = map_alert_to_task_payload(rule_code="air_humidity_low", severity="warning", title="X", message="X")
    assert p.priority == ProviderTaskPriority.HIGH


def test_unknown_rule_maps_to_maintenance():
    p = map_alert_to_task_payload(rule_code="unknown", severity="info", title="X", message="X")
    assert p.task_type == ProviderTaskType.MAINTENANCE


def test_build_task_key_stable():
    k1 = build_task_key(source_owner_tenant_id="o1", external_alert_id="alert-1", task_type="watering")
    k2 = build_task_key(source_owner_tenant_id="o1", external_alert_id="alert-1", task_type="watering")
    assert k1 == k2


# ============================================================================
# 6. Selectors
# ============================================================================


def test_list_open_tasks(monkeypatch):
    class FakeQS:
        def filter(self, **kw):
            return self
        def order_by(self, *a):
            return [SimpleNamespace(pk=1)]

    monkeypatch.setattr(
        "apps.provider_ops.selectors.task_selectors.ProviderTask",
        SimpleNamespace(objects=FakeQS()),
    )
    result = list_open_tasks()
    assert len(result) >= 1


def test_dashboard_summary(monkeypatch):
    class FakeCountQS:
        def filter(self, **kw):
            return self
        def count(self):
            return 5

    monkeypatch.setattr(
        "apps.provider_ops.selectors.task_selectors.ProviderTask",
        SimpleNamespace(objects=FakeCountQS()),
    )
    summary = task_dashboard_summary()
    assert summary["total"] == 5
