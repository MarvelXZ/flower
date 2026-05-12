"""Phase 2 tests for owner IoT ingest foundation."""

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from apps.devices.domain.enums import DeviceStatus, ProvisioningStatus
from apps.devices.services import provisioning_service
from apps.integrations.domain.enums import OutboxStatus
from apps.telemetry.services import mqtt_ingest_service, sensor_reading_service


@dataclass
class FakeDevice:
    uuid: UUID
    owner_tenant_schema: str
    status: str = DeviceStatus.ACTIVE
    is_active: bool = True
    last_seen_at: datetime | None = None
    saved_update_fields: list[str] | None = None

    def save(self, *, update_fields):
        self.saved_update_fields = list(update_fields)


class AtomicSpy:
    def __init__(self):
        self.active = False
        self.entered = False

    def __call__(self):
        return self

    def __enter__(self):
        self.active = True
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.active = False
        return False


def test_device_registration_uses_service(monkeypatch):
    created = {}
    now = datetime(2026, 5, 11, 10, 0, tzinfo=UTC)

    class FakeDeviceManager:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(**kwargs)

    monkeypatch.setattr(provisioning_service, "Device", SimpleNamespace(objects=FakeDeviceManager()))
    monkeypatch.setattr(provisioning_service.transaction, "atomic", lambda: nullcontext())
    monkeypatch.setattr(provisioning_service, "connection", SimpleNamespace(schema_name="owner"))
    monkeypatch.setattr(provisioning_service.timezone, "now", lambda: now)

    device = provisioning_service.register_device(name="ESP32 Office", serial_number="SN-001")

    assert device.name == "ESP32 Office"
    assert created["owner_tenant_schema"] == "owner"
    assert created["status"] == DeviceStatus.PROVISIONING
    assert created["provisioned_at"] == now
    assert created["serial_number"] == "SN-001"


def test_activate_and_deactivate_device_use_service():
    device = FakeDevice(uuid=uuid4(), owner_tenant_schema="owner", status=DeviceStatus.PROVISIONING)

    provisioning_service.activate_device(device=device)
    assert device.status == DeviceStatus.ACTIVE
    assert device.is_active is True
    assert "activated_at" in device.saved_update_fields

    provisioning_service.deactivate_device(device=device)
    assert device.status == DeviceStatus.RETIRED
    assert device.is_active is False


def test_sensor_reading_service_creates_reading_and_outbox_in_one_transaction(monkeypatch):
    atomic = AtomicSpy()
    device_uuid = uuid4()
    measured_at = datetime(2026, 5, 11, 10, 5, tzinfo=UTC)
    device = FakeDevice(uuid=device_uuid, owner_tenant_schema="owner")
    created = {"reading": None, "outbox": None}

    class FakeReadingManager:
        def create(self, **kwargs):
            assert atomic.active is True
            created["reading"] = kwargs
            return SimpleNamespace(pk=123, **kwargs)

    class FakeOutboxManager:
        def create(self, **kwargs):
            assert atomic.active is True
            created["outbox"] = kwargs
            return SimpleNamespace(pk=456, **kwargs)

    monkeypatch.setattr(sensor_reading_service, "connection", SimpleNamespace(schema_name="owner"))
    monkeypatch.setattr(sensor_reading_service.transaction, "atomic", atomic)
    monkeypatch.setattr(sensor_reading_service, "SensorReading", SimpleNamespace(objects=FakeReadingManager()))
    monkeypatch.setattr(
        sensor_reading_service,
        "IntegrationOutbox",
        SimpleNamespace(objects=FakeOutboxManager()),
    )

    reading = sensor_reading_service.record_sensor_reading(
        device=device,
        measured_at=measured_at,
        soil_moisture=42.5,
        temperature=23.1,
        air_humidity=55.0,
        light_level=300,
        battery_level=87,
    )

    assert atomic.entered is True
    assert reading.pk == 123
    assert created["reading"]["device"] is device
    assert device.last_seen_at == measured_at
    assert created["outbox"]["event_type"] == "SensorReadingReceived"
    assert created["outbox"]["aggregate_type"] == "SensorReading"
    assert created["outbox"]["status"] == OutboxStatus.PENDING
    assert created["outbox"]["payload"]["device_uuid"] == str(device_uuid)


def test_sensor_reading_service_fails_closed_outside_owner_context(monkeypatch):
    device = FakeDevice(uuid=uuid4(), owner_tenant_schema="owner")
    monkeypatch.setattr(sensor_reading_service, "connection", SimpleNamespace(schema_name="provider"))

    with pytest.raises(sensor_reading_service.TenantIsolationError):
        sensor_reading_service.record_sensor_reading(
            device=device,
            measured_at=datetime(2026, 5, 11, 10, 5, tzinfo=UTC),
        )


def test_valid_mqtt_payload_creates_sensor_reading_and_outbox(monkeypatch):
    atomic = AtomicSpy()
    device_uuid = uuid4()
    device = FakeDevice(uuid=device_uuid, owner_tenant_schema="owner")
    created = {"reading": None, "outbox": None}

    class FakeReadingManager:
        def create(self, **kwargs):
            created["reading"] = kwargs
            return SimpleNamespace(pk=789, **kwargs)

    class FakeOutboxManager:
        def create(self, **kwargs):
            created["outbox"] = kwargs
            return SimpleNamespace(pk=100, **kwargs)

    class FakeDeviceModel:
        class DoesNotExist(Exception):
            pass

        class objects:
            @staticmethod
            def get(*, uuid):
                assert uuid == device_uuid
                return device

    monkeypatch.setattr(mqtt_ingest_service, "Device", FakeDeviceModel)
    monkeypatch.setattr(sensor_reading_service, "connection", SimpleNamespace(schema_name="owner"))
    monkeypatch.setattr(sensor_reading_service.transaction, "atomic", atomic)
    monkeypatch.setattr(sensor_reading_service, "SensorReading", SimpleNamespace(objects=FakeReadingManager()))
    monkeypatch.setattr(
        sensor_reading_service,
        "IntegrationOutbox",
        SimpleNamespace(objects=FakeOutboxManager()),
    )

    reading = mqtt_ingest_service.ingest_telemetry_payload(
        topic=f"devices/{device_uuid}/telemetry",
        payload={
            "schema_version": "1.0",
            "device_uuid": str(device_uuid),
            "measured_at": "2026-05-11T10:05:00Z",
            "soil_moisture": 42.5,
            "temperature": 23.1,
            "air_humidity": 55.0,
            "light_level": 300,
            "battery_level": 87,
        },
    )

    assert reading.pk == 789
    assert created["reading"]["soil_moisture"] == 42.5
    assert created["outbox"]["event_type"] == "SensorReadingReceived"
    assert created["outbox"]["payload"]["battery_level"] == 87


def test_unknown_device_uuid_fails_closed(monkeypatch):
    device_uuid = uuid4()

    class FakeDeviceModel:
        class DoesNotExist(Exception):
            pass

        class objects:
            @staticmethod
            def get(*, uuid):
                raise FakeDeviceModel.DoesNotExist()

    monkeypatch.setattr(mqtt_ingest_service, "Device", FakeDeviceModel)

    with pytest.raises(mqtt_ingest_service.UnknownDeviceError):
        mqtt_ingest_service.ingest_telemetry_payload(
            topic=f"devices/{device_uuid}/telemetry",
            payload={
                "schema_version": "1.0",
                "device_uuid": str(device_uuid),
                "measured_at": "2026-05-11T10:05:00Z",
                "temperature": 23.1,
            },
        )


def test_invalid_schema_version_fails_closed_before_device_lookup(monkeypatch):
    device_uuid = uuid4()

    class FakeDeviceModel:
        class objects:
            @staticmethod
            def get(*, uuid):
                raise AssertionError("Device lookup must not happen for invalid payloads.")

    monkeypatch.setattr(mqtt_ingest_service, "Device", FakeDeviceModel)

    with pytest.raises(mqtt_ingest_service.InvalidTelemetryPayloadError):
        mqtt_ingest_service.ingest_telemetry_payload(
            topic=f"devices/{device_uuid}/telemetry",
            payload={
                "schema_version": "2.0",
                "device_uuid": str(device_uuid),
                "measured_at": "2026-05-11T10:05:00Z",
                "temperature": 23.1,
            },
        )
