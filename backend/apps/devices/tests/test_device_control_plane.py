"""Unit tests for Device Control Plane — provisioning, heartbeat, MQTT ACL, shadow.

Uses mock objects to avoid database access, following the same FakeModel
pattern used across the project.
"""

from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.devices.domain.enums import DeviceStatus, ProvisioningStatus
from apps.devices.services.provisioning_service import (
    DeviceOfflineError,
    DeviceProvisioningError,
    activate_device,
    complete_provisioning,
    create_device_credentials,
    deactivate_device,
    detect_offline_devices,
    mark_device_offline,
    mark_device_online,
    record_heartbeat,
    register_device,
)
from apps.devices.services.mqtt_acl_service import (
    MqttAclError,
    MqttTopic,
    TenantIsolationError,
    DeviceSpoofingError,
    build_device_topic,
    build_provider_topic,
    validate_device_publish,
    validate_device_subscribe,
)


# ---------------------------------------------------------------------------
# MQTT Topic parsing
# ---------------------------------------------------------------------------

def test_parse_valid_telemetry_topic():
    topic = MqttTopic.parse("tenant/owner_1/device/ESP32-001/telemetry")
    assert topic is not None
    assert topic.tenant_schema == "owner_1"
    assert topic.device_serial == "ESP32-001"
    assert topic.action == "telemetry"


def test_parse_valid_heartbeat_topic():
    topic = MqttTopic.parse("tenant/owner_1/device/ESP32-001/heartbeat")
    assert topic is not None
    assert topic.action == "heartbeat"


def test_parse_valid_shadow_reported_topic():
    topic = MqttTopic.parse("tenant/owner_1/device/ESP32-001/shadow/reported")
    assert topic is not None
    assert topic.action == "shadow/reported"


def test_parse_invalid_topic_too_short():
    assert MqttTopic.parse("tenant/owner_1/device") is None


def test_parse_invalid_topic_no_tenant_prefix():
    assert MqttTopic.parse("other/owner_1/device/ESP32-001/telemetry") is None


# ---------------------------------------------------------------------------
# MQTT ACL — device publish validation
# ---------------------------------------------------------------------------

def test_device_can_publish_telemetry_in_own_tenant():
    validate_device_publish(
        topic="tenant/owner_1/device/ESP32-001/telemetry",
        client_id="ESP32-001",
        tenant_schema="owner_1",
    )  # no raise


def test_device_cannot_publish_to_other_tenant():
    with pytest.raises(TenantIsolationError):
        validate_device_publish(
            topic="tenant/owner_2/device/ESP32-001/telemetry",
            client_id="ESP32-001",
            tenant_schema="owner_1",
        )


def test_device_cannot_spoof_other_device():
    with pytest.raises(DeviceSpoofingError):
        validate_device_publish(
            topic="tenant/owner_1/device/ESP32-002/telemetry",
            client_id="ESP32-001",
            tenant_schema="owner_1",
        )


def test_device_cannot_publish_to_forbidden_action():
    with pytest.raises(MqttAclError):
        validate_device_publish(
            topic="tenant/owner_1/device/ESP32-001/shadow/desired",
            client_id="ESP32-001",
            tenant_schema="owner_1",
        )


def test_device_can_publish_heartbeat():
    validate_device_publish(
        topic="tenant/owner_1/device/ESP32-001/heartbeat",
        client_id="ESP32-001",
        tenant_schema="owner_1",
    )  # no raise


# ---------------------------------------------------------------------------
# MQTT ACL — device subscribe validation
# ---------------------------------------------------------------------------

def test_device_can_subscribe_to_shadow_desired():
    validate_device_subscribe(
        topic="tenant/owner_1/device/ESP32-001/shadow/desired",
        client_id="ESP32-001",
        tenant_schema="owner_1",
    )  # no raise


def test_device_can_subscribe_to_ota_update():
    validate_device_subscribe(
        topic="tenant/owner_1/device/ESP32-001/ota/update",
        client_id="ESP32-001",
        tenant_schema="owner_1",
    )  # no raise


def test_device_cannot_subscribe_to_telemetry():
    with pytest.raises(MqttAclError):
        validate_device_subscribe(
            topic="tenant/owner_1/device/ESP32-001/telemetry",
            client_id="ESP32-001",
            tenant_schema="owner_1",
        )


# ---------------------------------------------------------------------------
# topic builders
# ---------------------------------------------------------------------------

def test_build_device_topic():
    assert build_device_topic(
        tenant_schema="owner_1",
        device_serial="ESP32-001",
        action="telemetry",
    ) == "tenant/owner_1/device/ESP32-001/telemetry"


def test_build_provider_topic():
    assert build_provider_topic(
        tenant_schema="owner_1",
        provider_schema="provider_1",
        action="cmd",
    ) == "tenant/owner_1/provider/provider_1/cmd"


# ---------------------------------------------------------------------------
# Provisioning lifecycle
# ---------------------------------------------------------------------------

def _patch_provisioning(monkeypatch):
    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.transaction.atomic",
        lambda: nullcontext(),
    )
    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.connection",
        SimpleNamespace(schema_name="owner_1"),
    )
    # Mock record_transition (imported into provisioning_service) to avoid DB
    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.record_transition",
        lambda **kwargs: None,
    )
    # Mock _emit_device_event to avoid DB access
    monkeypatch.setattr(
        "apps.devices.services.provisioning_service._emit_device_event",
        lambda **kwargs: None,
    )


def test_register_device_creates_with_correct_defaults(monkeypatch):
    _patch_provisioning(monkeypatch)
    created = {}

    class FakeDeviceManager:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.Device",
        SimpleNamespace(objects=FakeDeviceManager()),
    )

    device = register_device(
        name="ESP32 Office",
        serial_number="ESP32-001",
        hardware_revision="v1.2",
        capabilities=["temperature", "humidity"],
    )

    assert device.name == "ESP32 Office"
    assert created["serial_number"] == "ESP32-001"
    assert created["provisioning_status"] == ProvisioningStatus.UNPROVISIONED
    assert created["status"] == DeviceStatus.PROVISIONING
    assert created["owner_tenant_schema"] == "owner_1"


def test_register_device_rejects_public_schema(monkeypatch):
    _patch_provisioning(monkeypatch)
    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.connection",
        SimpleNamespace(schema_name="public"),
    )

    with pytest.raises(DeviceProvisioningError):
        register_device(name="Test", serial_number="SN-001")


def test_activate_device_transitions_correctly(monkeypatch):
    _patch_provisioning(monkeypatch)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    device = SimpleNamespace(
        status=DeviceStatus.PROVISIONING,
        provisioning_status=ProvisioningStatus.REGISTERED,
        is_active=True,
        saved_fields=None,
    )

    def fake_save(*, update_fields):
        device.saved_fields = list(update_fields)

    device.save = fake_save

    result = activate_device(device=device)

    assert result.status == DeviceStatus.ACTIVE
    assert result.provisioning_status == ProvisioningStatus.ACTIVATED
    assert result.activated_at == now
    assert "status" in result.saved_fields


def test_deactivate_device_retires_without_deleting(monkeypatch):
    _patch_provisioning(monkeypatch)
    device = SimpleNamespace(
        status=DeviceStatus.ACTIVE,
        is_active=True,
        saved_fields=None,
    )

    def fake_save(*, update_fields):
        device.saved_fields = list(update_fields)

    device.save = fake_save

    result = deactivate_device(device=device)

    assert result.status == DeviceStatus.RETIRED
    assert result.is_active is False


# ---------------------------------------------------------------------------
# Offline detection
# ---------------------------------------------------------------------------

def test_detect_offline_device_with_no_heartbeat(monkeypatch):
    """Device with last_seen_at=None should be detected as offline."""
    now = timezone.now()
    offline_device = SimpleNamespace(
        last_seen_at=None,
        heartbeat_interval_seconds=60,
        status=DeviceStatus.ACTIVE,
    )
    online_device = SimpleNamespace(
        last_seen_at=now - timedelta(seconds=10),
        heartbeat_interval_seconds=60,
        status=DeviceStatus.ACTIVE,
    )

    monkeypatch.setattr(
        "apps.devices.services.provisioning_service.Device",
        SimpleNamespace(objects=SimpleNamespace(
            filter=lambda **kw: [offline_device, online_device],
        )),
    )

    result = detect_offline_devices(owner_tenant_schema="owner_1")

    assert offline_device in result
    assert online_device not in result


def test_mark_offline_only_from_active(monkeypatch):
    _patch_provisioning(monkeypatch)
    device = SimpleNamespace(status=DeviceStatus.OFFLINE)

    with pytest.raises(DeviceOfflineError):
        mark_device_offline(device=device)


def test_mark_online_transitions_back_to_active(monkeypatch):
    _patch_provisioning(monkeypatch)
    device = SimpleNamespace(
        status=DeviceStatus.OFFLINE,
        saved_fields=None,
    )

    def fake_save(*, update_fields):
        device.saved_fields = list(update_fields)

    device.save = fake_save

    result = mark_device_online(device=device)

    assert result.status == DeviceStatus.ACTIVE
