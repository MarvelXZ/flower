"""Unit tests for Device Event Bus + State Machine + Audit Trail.

Uses mock objects following the same FakeModel pattern established across
the project.  No database access required.
"""

import pytest

from apps.devices.domain.enums import ProvisioningStatus
from apps.devices.domain.state_machine import (
    DeviceStateTransitionError,
    can_transition,
    is_terminal,
    validate_transition,
)
from apps.devices.events import (
    DeviceEvent,
    DeviceEventType,
    clear_subscribers,
    emit,
    subscribe,
    unsubscribe,
)


# ---------------------------------------------------------------------------
# Event Bus
# ---------------------------------------------------------------------------

def test_event_creation_produces_valid_event():
    event = DeviceEvent.create(
        event_type=DeviceEventType.PROVISIONED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
        data={"hardware_revision": "v1.2"},
    )
    assert event.event_type == DeviceEventType.PROVISIONED
    assert event.device_serial == "ESP32-001"
    assert event.data["hardware_revision"] == "v1.2"
    assert len(event.event_id) == 36  # UUID4


def test_event_creation_rejects_unknown_type():
    with pytest.raises(ValueError):
        DeviceEvent.create(
            event_type="device.nonexistent",
            device_serial="ESP32-001",
            device_uuid="uuid-1",
            tenant_schema="owner_1",
        )


def test_event_is_immutable():
    event = DeviceEvent.create(
        event_type=DeviceEventType.ACTIVATED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )
    with pytest.raises(Exception):
        event.event_type = "changed"


def test_subscriber_receives_event():
    clear_subscribers()
    received = []

    def handler(event):
        received.append(event)

    subscribe(handler)
    event = DeviceEvent.create(
        event_type=DeviceEventType.HEARTBEAT_RECEIVED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )
    emit(event)

    assert len(received) == 1
    assert received[0].event_id == event.event_id
    assert received[0].event_type == DeviceEventType.HEARTBEAT_RECEIVED


def test_unsubscribed_handler_does_not_receive():
    clear_subscribers()
    received = []

    def handler(event):
        received.append(event)

    subscribe(handler)
    unsubscribe(handler)
    event = DeviceEvent.create(
        event_type=DeviceEventType.OFFLINE,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )
    emit(event)

    assert len(received) == 0


def test_failing_subscriber_does_not_block_others():
    clear_subscribers()
    received = []

    def bad_handler(event):
        raise RuntimeError("subscriber failed")

    def good_handler(event):
        received.append(event)

    subscribe(bad_handler)
    subscribe(good_handler)
    event = DeviceEvent.create(
        event_type=DeviceEventType.ONLINE,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )
    emit(event)  # should not raise

    assert len(received) == 1


def test_multiple_subscribers_all_receive():
    clear_subscribers()
    results = []

    def handler_a(event):
        results.append("a")

    def handler_b(event):
        results.append("b")

    subscribe(handler_a)
    subscribe(handler_b)
    event = DeviceEvent.create(
        event_type=DeviceEventType.SHADOW_REPORTED,
        device_serial="ESP32-001",
        device_uuid="uuid-1",
        tenant_schema="owner_1",
    )
    emit(event)

    assert results == ["a", "b"]


def test_all_event_types_are_valid():
    for event_type in [
        DeviceEventType.PROVISIONED,
        DeviceEventType.IDENTITY_CREATED,
        DeviceEventType.REGISTERED,
        DeviceEventType.ACTIVATED,
        DeviceEventType.DEACTIVATED,
        DeviceEventType.OFFLINE,
        DeviceEventType.ONLINE,
        DeviceEventType.HEARTBEAT_RECEIVED,
        DeviceEventType.SHADOW_REPORTED,
        DeviceEventType.SHADOW_DESIRED,
        DeviceEventType.FIRMWARE_ASSIGNED,
        DeviceEventType.FIRMWARE_COMPLETED,
        DeviceEventType.FIRMWARE_FAILED,
        DeviceEventType.CREDENTIAL_ROTATED,
        DeviceEventType.PROVISIONING_FAILED,
    ]:
        event = DeviceEvent.create(
            event_type=event_type,
            device_serial="ESP32-001",
            device_uuid="uuid-1",
            tenant_schema="owner_1",
        )
        assert event.event_type == event_type


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------


def test_unprovisioned_to_identity_created_is_allowed():
    validate_transition(
        current_status=ProvisioningStatus.UNPROVISIONED,
        target_status=ProvisioningStatus.IDENTITY_CREATED,
    )  # no raise


def test_unprovisioned_to_failed_is_allowed():
    validate_transition(
        current_status=ProvisioningStatus.UNPROVISIONED,
        target_status=ProvisioningStatus.FAILED,
    )  # no raise


def test_activated_to_unprovisioned_is_blocked():
    """Cannot go backwards from ACTIVATED to UNPROVISIONED."""
    with pytest.raises(DeviceStateTransitionError):
        validate_transition(
            current_status=ProvisioningStatus.ACTIVATED,
            target_status=ProvisioningStatus.UNPROVISIONED,
        )


def test_activated_to_identity_created_is_blocked():
    """Cannot downgrade a live device."""
    with pytest.raises(DeviceStateTransitionError):
        validate_transition(
            current_status=ProvisioningStatus.ACTIVATED,
            target_status=ProvisioningStatus.IDENTITY_CREATED,
        )


def test_failed_is_terminal():
    assert is_terminal(ProvisioningStatus.FAILED) is True
    for target in ProvisioningStatus.values:
        if target == ProvisioningStatus.FAILED:
            continue
        assert can_transition(
            current_status=ProvisioningStatus.FAILED,
            target_status=target,
        ) is False


def test_full_lifecycle_is_allowed():
    """UNPROVISIONED → IDENTITY_CREATED → REGISTERED → ACTIVATED is valid."""
    assert can_transition(
        current_status=ProvisioningStatus.UNPROVISIONED,
        target_status=ProvisioningStatus.IDENTITY_CREATED,
    )
    assert can_transition(
        current_status=ProvisioningStatus.IDENTITY_CREATED,
        target_status=ProvisioningStatus.REGISTERED,
    )
    assert can_transition(
        current_status=ProvisioningStatus.REGISTERED,
        target_status=ProvisioningStatus.ACTIVATED,
    )


def test_skip_certificate_is_allowed():
    """IDENTITY_CREATED → REGISTERED (skip CERTIFICATE_ISSUED) is valid."""
    assert can_transition(
        current_status=ProvisioningStatus.IDENTITY_CREATED,
        target_status=ProvisioningStatus.REGISTERED,
    )


def test_skip_registered_is_blocked():
    """IDENTITY_CREATED → ACTIVATED is not allowed (must go through REGISTERED)."""
    assert not can_transition(
        current_status=ProvisioningStatus.IDENTITY_CREATED,
        target_status=ProvisioningStatus.ACTIVATED,
    )


def test_unknown_status_raises():
    with pytest.raises(DeviceStateTransitionError):
        validate_transition(
            current_status="nonexistent_status",
            target_status=ProvisioningStatus.ACTIVATED,
        )


def test_activated_can_fail():
    """ACTIVATED → FAILED is allowed (decommission)."""
    assert can_transition(
        current_status=ProvisioningStatus.ACTIVATED,
        target_status=ProvisioningStatus.FAILED,
    )
