"""Unit tests for Alert lifecycle service (Phase 11)."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.notifications.domain.enums import AlertSeverity, AlertStatus
from apps.notifications.services.alert_service import (
    InvalidAlertTransition,
    _active_alert_exists,
    _validate_transition,
    acknowledge_alert,
    dismiss_alert,
    open_or_update_alert,
    resolve_alert,
)


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.transaction.atomic",
        lambda: nullcontext(),
    )


def _make_existing_alert(alert_key="test:device_1", status=AlertStatus.OPEN):
    return SimpleNamespace(
        pk=1,
        alert_key=alert_key,
        status=status,
        severity=AlertSeverity.WARNING,
        last_seen_at=timezone.now(),
        metadata={},
        save=MagicMock(),
    )


# ============================================================================
# _validate_transition
# ============================================================================


def test_open_to_acknowledged_allowed():
    _validate_transition(AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)


def test_open_to_resolved_allowed():
    _validate_transition(AlertStatus.OPEN, AlertStatus.RESOLVED)


def test_open_to_dismissed_allowed():
    _validate_transition(AlertStatus.OPEN, AlertStatus.DISMISSED)


def test_acknowledged_to_resolved_allowed():
    _validate_transition(AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED)


def test_acknowledged_to_dismissed_allowed():
    _validate_transition(AlertStatus.ACKNOWLEDGED, AlertStatus.DISMISSED)


def test_resolved_is_terminal():
    for target in AlertStatus.values:
        if target == AlertStatus.RESOLVED:
            continue
        with pytest.raises(InvalidAlertTransition):
            _validate_transition(AlertStatus.RESOLVED, target)


def test_dismissed_is_terminal():
    for target in AlertStatus.values:
        if target == AlertStatus.DISMISSED:
            continue
        with pytest.raises(InvalidAlertTransition):
            _validate_transition(AlertStatus.DISMISSED, target)


def test_open_to_open_denied():
    with pytest.raises(InvalidAlertTransition):
        _validate_transition(AlertStatus.OPEN, AlertStatus.OPEN)


# ============================================================================
# _active_alert_exists
# ============================================================================


def test_active_alert_exists_found(monkeypatch):
    fake = _make_existing_alert()

    class FakeQS:
        def get(self, **kw):
            return fake

    monkeypatch.setattr(
        "apps.notifications.services.alert_service.Alert",
        SimpleNamespace(objects=FakeQS()),
    )

    result = _active_alert_exists(alert_key="test:device_1")
    assert result is not None


def test_active_alert_exists_not_found(monkeypatch):
    class DNE(Exception):
        pass

    class FakeQS:
        def get(self, **kw):
            raise DNE()

    monkeypatch.setattr(
        "apps.notifications.services.alert_service.Alert",
        SimpleNamespace(objects=FakeQS(), DoesNotExist=DNE),
    )

    result = _active_alert_exists(alert_key="test:device_1")
    assert result is None


# ============================================================================
# open_or_update_alert
# ============================================================================


def test_open_or_update_alert_creates_new(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.timezone",
        SimpleNamespace(now=lambda: now),
    )
    monkeypatch.setattr(
        "apps.notifications.services.alert_service._active_alert_exists",
        lambda **kw: None,
    )
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.enqueue_alert_notification",
        lambda **kw: None,
    )

    class FakeAlert:
        objects = SimpleNamespace(
            create=MagicMock(
                side_effect=lambda **kw: SimpleNamespace(**kw | {"pk": 1})
            )
        )

    monkeypatch.setattr(
        "apps.notifications.services.alert_service.Alert",
        FakeAlert,
    )

    alert = open_or_update_alert(
        alert_key="test:device_1",
        title="Test alert",
        rule_code="test_rule",
    )
    assert alert.alert_key == "test:device_1"
    assert alert.status == AlertStatus.OPEN


def test_open_or_update_alert_updates_existing(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    existing = _make_existing_alert()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service._active_alert_exists",
        lambda **kw: existing,
    )

    result = open_or_update_alert(
        alert_key="test:device_1",
        title="Updated",
    )
    assert result.last_seen_at == now
    existing.save.assert_called_once()


def test_open_or_update_alert_same_key_no_duplicate(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    existing = _make_existing_alert()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service._active_alert_exists",
        lambda **kw: existing,
    )

    # Second call with same key should update, not create
    result = open_or_update_alert(
        alert_key="test:device_1",
        title="Still open",
    )
    assert result is existing
    assert result.last_seen_at is not None


# ============================================================================
# acknowledge_alert
# ============================================================================


def test_acknowledge_alert_changes_status(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    fake = MagicMock()
    fake.status = AlertStatus.OPEN

    result = acknowledge_alert(alert=fake)
    assert result.status == AlertStatus.ACKNOWLEDGED
    assert result.acknowledged_at == now


def test_acknowledge_resolved_alert_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = AlertStatus.RESOLVED
    with pytest.raises(InvalidAlertTransition):
        acknowledge_alert(alert=fake)


# ============================================================================
# resolve_alert
# ============================================================================


def test_resolve_alert_changes_status(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.timezone",
        SimpleNamespace(now=lambda: now),
    )
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.enqueue_alert_notification",
        lambda **kw: None,
    )

    fake = MagicMock()
    fake.status = AlertStatus.OPEN

    result = resolve_alert(alert=fake)
    assert result.status == AlertStatus.RESOLVED
    assert result.resolved_at == now


def test_resolve_dismissed_alert_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = AlertStatus.DISMISSED
    with pytest.raises(InvalidAlertTransition):
        resolve_alert(alert=fake)


# ============================================================================
# dismiss_alert
# ============================================================================


def test_dismiss_alert_changes_status(monkeypatch):
    _mock_atomic(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    fake = MagicMock()
    fake.status = AlertStatus.OPEN

    result = dismiss_alert(alert=fake)
    assert result.status == AlertStatus.DISMISSED
    assert result.dismissed_at == now


def test_dismiss_resolved_alert_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    fake = MagicMock()
    fake.status = AlertStatus.RESOLVED
    with pytest.raises(InvalidAlertTransition):
        dismiss_alert(alert=fake)
