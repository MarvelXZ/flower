"""Unit tests for SLA & escalation engine (Phase 15)."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock


from apps.provider_ops.domain.enums import (
    ProviderTaskPriority,
    ProviderTaskStatus,
    TaskEscalationType,
)
from apps.provider_ops.services.sla_policy_service import (
    get_priority_sla,
    get_task_sla_policy,
)
from apps.provider_ops.services.sla_service import (
    create_task_sla,
    evaluate_all_open_task_slas,
    mark_task_assigned,
    mark_task_resolved,
    upgrade_task_priority,
)
from apps.provider_ops.selectors.sla_selectors import (
    list_breached_tasks,
    list_overdue_tasks,
    list_urgent_unassigned_tasks,
    sla_dashboard_summary,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.transaction.atomic",
        lambda: nullcontext(),
    )


def _make_task(priority=ProviderTaskPriority.NORMAL, status=ProviderTaskStatus.OPEN, **kw):
    defaults = {
        "pk": 1,
        "task_key": "t1",
        "priority": priority,
        "status": status,
        "title": "Test task",
        "assignee_id": "",
        "save": MagicMock(),
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ============================================================================
# 1. SLA Policy
# ============================================================================


def test_get_priority_sla_low():
    r, s = get_priority_sla(ProviderTaskPriority.LOW)
    assert r == 24.0
    assert s == 72.0


def test_get_priority_sla_normal():
    r, s = get_priority_sla(ProviderTaskPriority.NORMAL)
    assert r == 8.0
    assert s == 24.0


def test_get_priority_sla_high():
    r, s = get_priority_sla(ProviderTaskPriority.HIGH)
    assert r == 2.0
    assert s == 8.0


def test_get_priority_sla_urgent():
    r, s = get_priority_sla(ProviderTaskPriority.URGENT)
    assert r == 0.25
    assert s == 2.0


def test_get_task_sla_policy_returns_dict():
    policy = get_task_sla_policy(priority=ProviderTaskPriority.HIGH)
    assert policy["priority"] == ProviderTaskPriority.HIGH
    assert "response_due_at" in policy
    assert "resolution_due_at" in policy


# ============================================================================
# 2. SLA lifecycle
# ============================================================================


def test_create_task_sla(monkeypatch):
    _mock_atomic(monkeypatch)
    task = _make_task(priority=ProviderTaskPriority.URGENT)

    class FakeSLA:
        objects = SimpleNamespace(
            filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=None))),
            create=MagicMock(return_value=SimpleNamespace(pk=1, task=task)),
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskSLA",
        FakeSLA,
    )

    sla = create_task_sla(task=task)
    assert sla is not None


def test_mark_task_assigned_first_time(monkeypatch):
    _mock_atomic(monkeypatch)
    task = _make_task()

    class FakeSLA:
        objects = SimpleNamespace(
            get_or_create=MagicMock(
                return_value=(SimpleNamespace(first_assigned_at=None, save=MagicMock()), True)
            ),
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskSLA",
        FakeSLA,
    )

    sla = mark_task_assigned(task=task)
    assert sla.first_assigned_at is not None


def test_mark_task_resolved(monkeypatch):
    _mock_atomic(monkeypatch)
    task = _make_task()

    class FakeSLA:
        objects = SimpleNamespace(
            get_or_create=MagicMock(
                return_value=(SimpleNamespace(resolved_at=None, save=MagicMock()), False)
            ),
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskSLA",
        FakeSLA,
    )

    sla = mark_task_resolved(task=task)
    assert sla.resolved_at is not None


# ============================================================================
# 3. Escalation
# ============================================================================


def test_escalation_event_created(monkeypatch):
    _mock_atomic(monkeypatch)
    task = _make_task()
    called = []

    class FakeSLA:
        objects = SimpleNamespace(
            get_or_create=MagicMock(
                return_value=(SimpleNamespace(escalation_level=0, last_escalated_at=None, save=MagicMock()), True)
            ),
        )

    class FakeEvent:
        objects = SimpleNamespace(
            create=MagicMock(side_effect=lambda **kw: called.append(kw) or SimpleNamespace(pk=1))
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskSLA",
        FakeSLA,
    )
    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskEscalationEvent",
        FakeEvent,
    )
    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service._enqueue_escalation_notification",
        lambda **kw: None,
    )

    from apps.provider_ops.services.sla_service import _escalate_task
    ev = _escalate_task(task=task, escalation_type=TaskEscalationType.OVERDUE)
    assert ev is not None
    assert len(called) >= 1


def test_upgrade_priority_escalation(monkeypatch):
    _mock_atomic(monkeypatch)
    task = _make_task(priority=ProviderTaskPriority.NORMAL)
    task.save = MagicMock()

    class FakeSLA:
        objects = SimpleNamespace(
            get_or_create=MagicMock(
                return_value=(SimpleNamespace(escalation_level=0, save=MagicMock()), True)
            ),
        )

    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskSLA",
        FakeSLA,
    )
    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.TaskEscalationEvent",
        SimpleNamespace(objects=SimpleNamespace(create=MagicMock(return_value=SimpleNamespace(pk=1)))),
    )
    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service._enqueue_escalation_notification",
        lambda **kw: None,
    )

    ev = upgrade_task_priority(task=task)
    assert ev is not None
    assert task.priority == ProviderTaskPriority.HIGH


def test_upgrade_priority_urgent_noop(monkeypatch):
    task = _make_task(priority=ProviderTaskPriority.URGENT)
    ev = upgrade_task_priority(task=task)
    assert ev is None


# ============================================================================
# 4. Evaluate SLA
# ============================================================================


def test_evaluate_all_open_task_slas(monkeypatch):
    monkeypatch.setattr(
        "apps.provider_ops.services.sla_service.ProviderTask",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=[])
            )
        ),
    )
    result = evaluate_all_open_task_slas()
    assert result["evaluated"] == 0


# ============================================================================
# 5. Selectors
# ============================================================================


def test_list_overdue_tasks(monkeypatch):
    class FakeQS:
        def filter(self, **kw):
            return self
        def select_related(self, *a):
            return self
        def order_by(self, *a):
            return [SimpleNamespace(pk=1)]

    monkeypatch.setattr(
        "apps.provider_ops.selectors.sla_selectors.ProviderTask",
        SimpleNamespace(objects=FakeQS()),
    )
    result = list_overdue_tasks()
    assert len(result) >= 1


def test_list_breached_tasks(monkeypatch):
    class FakeQS:
        def filter(self, *a, **kw):
            return self
        def select_related(self, *a):
            return self
        def order_by(self, *a):
            return [SimpleNamespace(pk=2)]

    monkeypatch.setattr(
        "apps.provider_ops.selectors.sla_selectors.ProviderTask",
        SimpleNamespace(objects=FakeQS()),
    )
    result = list_breached_tasks()
    assert len(result) >= 1


def test_list_urgent_unassigned(monkeypatch):
    class FakeQS:
        def filter(self, **kw):
            return self
        def order_by(self, *a):
            return [SimpleNamespace(pk=3)]

    monkeypatch.setattr(
        "apps.provider_ops.selectors.sla_selectors.ProviderTask",
        SimpleNamespace(objects=FakeQS()),
    )
    result = list_urgent_unassigned_tasks()
    assert len(result) >= 1


def test_sla_dashboard_summary(monkeypatch):
    class FakeCountQS:
        def filter(self, *a, **kw):
            return self
        def count(self):
            return 5

    monkeypatch.setattr(
        "apps.provider_ops.selectors.sla_selectors.ProviderTask",
        SimpleNamespace(objects=FakeCountQS()),
    )
    monkeypatch.setattr(
        "apps.provider_ops.selectors.sla_selectors.TaskEscalationEvent",
        SimpleNamespace(objects=SimpleNamespace(count=MagicMock(return_value=3))),
    )
    monkeypatch.setattr(
        "apps.provider_ops.selectors.sla_selectors.TaskSLA",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=SimpleNamespace(
                    aggregate=MagicMock(return_value={"avg": None})
                ))
            )
        ),
    )
    summary = sla_dashboard_summary()
    assert "overdue_count" in summary
