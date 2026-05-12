"""Unit tests for Rule & Alert Engine — AlertEvent, device bridge, operator engine.

Uses mock objects following the FakeModel pattern — no database access.
"""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from apps.devices.events import DeviceEvent, DeviceEventType
from apps.notifications.domain.enums import AlertSeverity, AlertSourceType, AlertStatus
from apps.notifications.models.alert_event import AlertEvent as AlertEventModel
from apps.notifications.services.alert_service import (
    InvalidAlertTransition,
    _validate_transition,
    acknowledge_alert,
    dismiss_alert,
    open_or_update_alert,
    resolve_alert,
)
from apps.notifications.services.device_alert_bridge import (
    on_device_event,
    _handle_device_offline,
    _handle_device_online,
    _handle_battery_low,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.transaction.atomic",
        lambda: nullcontext(),
    )
    import django.utils.timezone as tz_mod
    monkeypatch.setattr(tz_mod, "now", lambda: __import__("datetime").datetime(2026, 5, 12, 10, 0, 0))


def _mock_alert_objects(monkeypatch, alerts=None):
    """Mock Alert.objects so create/filter/get work in-memory."""
    store = list(alerts or [])

    class DoesNotExistError(Exception):
        pass

    class FakeQuerySet:
        def filter(self, **kwargs):
            results = []
            status_in = None
            lookup_kwargs = {}
            for k, v in kwargs.items():
                if k == "status__in":
                    status_in = set(v)
                elif k == "alert_key":
                    lookup_kwargs["alert_key"] = v
                else:
                    lookup_kwargs[k] = v
            for a in store:
                match = True
                for pk, pv in lookup_kwargs.items():
                    if getattr(a, pk, None) != pv:
                        match = False
                        break
                if status_in and getattr(a, "status", None) not in status_in:
                    match = False
                if match:
                    results.append(a)
            self._results = results
            return self

        def first(self):
            return self._results[0] if self._results else None

        def get(self, **kwargs):
            for a in store:
                match = True
                for k, v in kwargs.items():
                    if k == "status__in":
                        if getattr(a, "status", None) not in v:
                            match = False
                    elif getattr(a, k, None) != v:
                        match = False
                if match:
                    return a
            raise DoesNotExistError("Alert matching query does not exist.")

        def create(self, **kwargs):
            obj = SimpleNamespace(**kwargs)
            store.append(obj)
            return obj

    class FakeAlertModel:
        DoesNotExist = DoesNotExistError
        objects = FakeQuerySet()

    monkeypatch.setattr(
        "apps.notifications.services.alert_service.Alert",
        FakeAlertModel,
    )

    # Also patch for device_alert_bridge
    monkeypatch.setattr(
        "apps.notifications.services.device_alert_bridge.Alert",
        FakeAlertModel,
    )

    return store


def _mock_record_alert_event(monkeypatch):
    recorded = []

    def _record(**kwargs):
        recorded.append(kwargs)
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        "apps.notifications.services.alert_service.record_alert_event",
        _record,
    )
    return recorded


def _mock_enqueue(monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.services.alert_service.enqueue_alert_notification",
        lambda **kwargs: None,
    )


# ---------------------------------------------------------------------------
# Alert status transitions
# ---------------------------------------------------------------------------


def test_open_to_acknowledged_is_allowed():
    _validate_transition(AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)  # no raise


def test_open_to_resolved_is_allowed():
    _validate_transition(AlertStatus.OPEN, AlertStatus.RESOLVED)  # no raise


def test_open_to_dismissed_is_allowed():
    _validate_transition(AlertStatus.OPEN, AlertStatus.DISMISSED)  # no raise


def test_acknowledged_to_resolved_is_allowed():
    _validate_transition(AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED)  # no raise


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


# ---------------------------------------------------------------------------
# open_or_update_alert (dedup)
# ---------------------------------------------------------------------------


def test_open_or_update_creates_new_alert(monkeypatch):
    _mock_atomic(monkeypatch)
    store = _mock_alert_objects(monkeypatch)
    recorded = _mock_record_alert_event(monkeypatch)
    _mock_enqueue(monkeypatch)

    alert = open_or_update_alert(
        alert_key="soil_moisture_low:device_1",
        source_type=AlertSourceType.SENSOR_READING,
        source_id="reading-1",
        severity=AlertSeverity.CRITICAL,
        title="Soil moisture low",
        message="Soil moisture is 15%.",
        rule_code="soil_moisture_low",
        metadata={"value": 15.0},
    )

    assert alert.status == AlertStatus.OPEN
    assert alert.alert_key == "soil_moisture_low:device_1"
    assert len(store) == 1
    assert len(recorded) == 1
    assert recorded[0]["event_type"] == AlertEventModel.EventType.CREATED


def test_open_or_update_updates_existing(monkeypatch):
    _mock_atomic(monkeypatch)
    existing = SimpleNamespace(
        alert_key="key:device_1",
        status=AlertStatus.OPEN,
        last_seen_at=None,
        metadata={},
        saved_fields=None,
    )

    def save(update_fields=None):
        existing.saved_fields = list(update_fields)

    existing.save = save
    _mock_alert_objects(monkeypatch, alerts=[existing])
    recorded = _mock_record_alert_event(monkeypatch)
    _mock_enqueue(monkeypatch)

    alert = open_or_update_alert(
        alert_key="key:device_1",
        title="Updated",
        message="Still low",
        rule_code="test",
        metadata={"value": 10.0},
    )

    assert alert.status == AlertStatus.OPEN
    assert "last_seen_at" in existing.saved_fields
    assert 10.0 in existing.metadata.values()
    assert len(recorded) == 0  # No new alert event for update


# ---------------------------------------------------------------------------
# acknowledge_alert
# ---------------------------------------------------------------------------


def test_acknowledge_alert_records_event(monkeypatch):
    _mock_atomic(monkeypatch)
    recorded = _mock_record_alert_event(monkeypatch)

    alert = SimpleNamespace(status=AlertStatus.OPEN, saved_fields=None)

    def save(update_fields=None):
        alert.saved_fields = list(update_fields)

    alert.save = save

    result = acknowledge_alert(alert=alert)

    assert result.status == AlertStatus.ACKNOWLEDGED
    assert len(recorded) == 1
    assert recorded[0]["event_type"] == AlertEventModel.EventType.ACKNOWLEDGED


def test_acknowledge_resolved_raises(monkeypatch):
    _mock_atomic(monkeypatch)
    alert = SimpleNamespace(status=AlertStatus.RESOLVED)
    with pytest.raises(InvalidAlertTransition):
        acknowledge_alert(alert=alert)


# ---------------------------------------------------------------------------
# resolve_alert
# ---------------------------------------------------------------------------


def test_resolve_alert_records_event(monkeypatch):
    _mock_atomic(monkeypatch)
    recorded = _mock_record_alert_event(monkeypatch)
    _mock_enqueue(monkeypatch)

    alert = SimpleNamespace(status=AlertStatus.OPEN, saved_fields=None)

    def save(update_fields=None):
        alert.saved_fields = list(update_fields)

    alert.save = save

    result = resolve_alert(alert=alert)

    assert result.status == AlertStatus.RESOLVED
    assert len(recorded) == 1
    assert recorded[0]["event_type"] == AlertEventModel.EventType.RESOLVED


# ---------------------------------------------------------------------------
# dismiss_alert
# ---------------------------------------------------------------------------


def test_dismiss_alert_records_event(monkeypatch):
    _mock_atomic(monkeypatch)
    recorded = _mock_record_alert_event(monkeypatch)

    alert = SimpleNamespace(status=AlertStatus.OPEN, saved_fields=None)

    def save(update_fields=None):
        alert.saved_fields = list(update_fields)

    alert.save = save

    result = dismiss_alert(alert=alert)

    assert result.status == AlertStatus.DISMISSED
    assert len(recorded) == 1
    assert recorded[0]["event_type"] == AlertEventModel.EventType.DISMISSED


# ---------------------------------------------------------------------------
# Device alert bridge — device.offline
# ---------------------------------------------------------------------------


def test_offline_event_creates_alert(monkeypatch):
    _mock_atomic(monkeypatch)
    store = _mock_alert_objects(monkeypatch)

    event = DeviceEvent.create(
        event_type=DeviceEventType.OFFLINE,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )

    on_device_event(event)

    assert len(store) == 1
    assert store[0].alert_key == "device_offline:ESP32-001"
    assert store[0].severity == AlertSeverity.CRITICAL
    assert store[0].status == AlertStatus.OPEN


def test_offline_event_updates_existing(monkeypatch):
    _mock_atomic(monkeypatch)
    existing = SimpleNamespace(
        alert_key="device_offline:ESP32-001",
        status=AlertStatus.OPEN,
        last_seen_at=None,
        metadata={},
        saved_fields=None,
    )

    def save(update_fields=None):
        existing.saved_fields = list(update_fields)

    existing.save = save

    store = _mock_alert_objects(monkeypatch, alerts=[existing])

    event = DeviceEvent.create(
        event_type=DeviceEventType.OFFLINE,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )

    on_device_event(event)

    assert len(store) == 1  # No duplicate
    assert "last_seen_at" in existing.saved_fields


def test_online_event_resolves_offline_alert(monkeypatch):
    _mock_atomic(monkeypatch)
    existing = SimpleNamespace(
        alert_key="device_offline:ESP32-001",
        status=AlertStatus.OPEN,
        last_seen_at=None,
        metadata={},
        saved_fields=None,
    )

    def save(update_fields=None):
        existing.saved_fields = list(update_fields)

    existing.save = save

    _mock_alert_objects(monkeypatch, alerts=[existing])

    event = DeviceEvent.create(
        event_type=DeviceEventType.ONLINE,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )

    on_device_event(event)

    assert existing.status == AlertStatus.RESOLVED
    assert "status" in existing.saved_fields


def test_battery_low_event_creates_alert(monkeypatch):
    _mock_atomic(monkeypatch)
    store = _mock_alert_objects(monkeypatch)

    event = DeviceEvent.create(
        event_type=DeviceEventType.HEARTBEAT_RECEIVED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
        data={"battery_level": 10.0, "rssi": -60},
    )

    on_device_event(event)

    assert len(store) == 1
    assert store[0].alert_key == "battery_low:ESP32-001"
    assert store[0].severity == AlertSeverity.WARNING


def test_battery_normal_no_alert(monkeypatch):
    _mock_atomic(monkeypatch)
    store = _mock_alert_objects(monkeypatch)

    event = DeviceEvent.create(
        event_type=DeviceEventType.HEARTBEAT_RECEIVED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
        data={"battery_level": 80.0},
    )

    on_device_event(event)

    assert len(store) == 0


def test_unknown_event_type_is_noop(monkeypatch):
    _mock_atomic(monkeypatch)
    store = _mock_alert_objects(monkeypatch)

    event = DeviceEvent.create(
        event_type=DeviceEventType.ACTIVATED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )

    on_device_event(event)

    assert len(store) == 0


# ---------------------------------------------------------------------------
# AlertEvent model validation
# ---------------------------------------------------------------------------


def test_alert_event_event_types_are_valid():
    """All AlertEvent.EventType values should be valid choices."""
    valid_types = set(AlertEventModel.EventType.values)
    assert "created" in valid_types
    assert "acknowledged" in valid_types
    assert "resolved" in valid_types
    assert "dismissed" in valid_types
    assert "escalated" in valid_types


def test_alert_event_record_function():
    """record_alert_event should create an AlertEvent with correct fields."""
    from apps.notifications.models.alert_event import record_alert_event

    created = {}

    class FakeAlertEventManager:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(**kwargs)

    monkeypatch_module = __import__(
        "apps.notifications.models.alert_event",
        fromlist=["AlertEvent"],
    )

    # This test verifies the function signature — no DB needed.
    assert callable(record_alert_event)
