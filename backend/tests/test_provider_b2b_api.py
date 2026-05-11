"""Phase 4 tests for provider inbound B2B API skeleton."""

from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.provider_ops.api.views import LocationUpsertView, TelemetryBatchView
from apps.provider_ops.services import idempotency_service, inbound_service


class InMemoryUpsertManager:
    def __init__(self):
        self.records = {}

    def update_or_create(self, *, source_owner_tenant_id, external_id=None, external_reading_id=None, defaults):
        key = (source_owner_tenant_id, external_id or external_reading_id)
        created = key not in self.records
        if created:
            self.records[key] = SimpleNamespace(
                source_owner_tenant_id=source_owner_tenant_id,
                external_id=external_id,
                external_reading_id=external_reading_id,
            )
        for field, value in defaults.items():
            setattr(self.records[key], field, value)
        return self.records[key], created


class InMemoryIdempotencyManager:
    def __init__(self):
        self.records = {}

    def filter(self, *, key, endpoint):
        record = self.records.get((key, endpoint))
        return SimpleNamespace(first=lambda: record)

    def create(self, **kwargs):
        record = SimpleNamespace(**kwargs)
        self.records[(kwargs["key"], kwargs["endpoint"])] = record
        return record


def _provider_context(monkeypatch):
    monkeypatch.setattr(inbound_service, "connection", SimpleNamespace(schema_name="provider"))
    monkeypatch.setattr(inbound_service.transaction, "atomic", lambda: nullcontext())


def test_location_upsert_creates_external_location(monkeypatch):
    _provider_context(monkeypatch)
    manager = InMemoryUpsertManager()
    monkeypatch.setattr(inbound_service, "ExternalLocation", SimpleNamespace(objects=manager))

    location, created = inbound_service.upsert_external_location(
        source_owner_tenant_id="owner",
        external_id="loc-1",
        name="Office",
        address="Main street",
        raw_payload={"external_id": "loc-1"},
    )

    assert created is True
    assert location.external_id == "loc-1"
    assert location.name == "Office"
    assert len(manager.records) == 1


def test_repeated_location_upsert_updates_same_record(monkeypatch):
    _provider_context(monkeypatch)
    manager = InMemoryUpsertManager()
    monkeypatch.setattr(inbound_service, "ExternalLocation", SimpleNamespace(objects=manager))

    first, first_created = inbound_service.upsert_external_location(
        source_owner_tenant_id="owner",
        external_id="loc-1",
        name="Office",
    )
    second, second_created = inbound_service.upsert_external_location(
        source_owner_tenant_id="owner",
        external_id="loc-1",
        name="Updated office",
    )

    assert first is second
    assert first_created is True
    assert second_created is False
    assert second.name == "Updated office"
    assert len(manager.records) == 1


def test_device_upsert_creates_external_device(monkeypatch):
    _provider_context(monkeypatch)
    manager = InMemoryUpsertManager()
    monkeypatch.setattr(inbound_service, "ExternalDevice", SimpleNamespace(objects=manager))

    device, created = inbound_service.upsert_external_device(
        source_owner_tenant_id="owner",
        external_id="dev-1",
        name="ESP32",
        status="active",
    )

    assert created is True
    assert device.external_id == "dev-1"
    assert device.name == "ESP32"
    assert device.status == "active"


def test_telemetry_batch_creates_ingest_records(monkeypatch):
    _provider_context(monkeypatch)
    device = SimpleNamespace(external_id="dev-1")
    ingest_manager = InMemoryUpsertManager()

    class FakeExternalDevice:
        class DoesNotExist(Exception):
            pass

        class objects:
            @staticmethod
            def get(*, source_owner_tenant_id, external_id):
                assert source_owner_tenant_id == "owner"
                assert external_id == "dev-1"
                return device

    monkeypatch.setattr(inbound_service, "ExternalDevice", FakeExternalDevice)
    monkeypatch.setattr(inbound_service, "TelemetryIngest", SimpleNamespace(objects=ingest_manager))

    ingested = inbound_service.ingest_telemetry_batch(
        source_owner_tenant_id="owner",
        readings=[
            {
                "external_device_id": "dev-1",
                "external_reading_id": "reading-1",
                "measured_at": "2026-05-11T10:05:00Z",
                "temperature": 23.1,
            }
        ],
    )

    assert len(ingested) == 1
    assert ingested[0].external_device is device
    assert ingested[0].temperature == 23.1
    assert len(ingest_manager.records) == 1


def test_unknown_device_in_telemetry_batch_fails_closed(monkeypatch):
    _provider_context(monkeypatch)

    class FakeExternalDevice:
        class DoesNotExist(Exception):
            pass

        class objects:
            @staticmethod
            def get(*, source_owner_tenant_id, external_id):
                raise FakeExternalDevice.DoesNotExist()

    monkeypatch.setattr(inbound_service, "ExternalDevice", FakeExternalDevice)

    with pytest.raises(inbound_service.UnknownExternalDeviceError):
        inbound_service.ingest_telemetry_batch(
            source_owner_tenant_id="owner",
            readings=[
                {
                    "external_device_id": "unknown",
                    "external_reading_id": "reading-1",
                    "measured_at": "2026-05-11T10:05:00Z",
                }
            ],
        )


@override_settings(B2B_TEST_API_KEY="secret")
def test_invalid_api_key_is_rejected():
    request = APIRequestFactory().post(
        "/api/b2b/v1/locations/upsert/",
        {
            "source_owner_tenant_id": "owner",
            "external_id": "loc-1",
            "name": "Office",
        },
        format="json",
        HTTP_X_PROVIDER_API_KEY="wrong",
        HTTP_X_IDEMPOTENCY_KEY="idem-1",
    )

    response = LocationUpsertView.as_view()(request)

    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


@override_settings(B2B_TEST_API_KEY="secret")
def test_missing_idempotency_key_is_rejected(monkeypatch):
    request = APIRequestFactory().post(
        "/api/b2b/v1/locations/upsert/",
        {
            "source_owner_tenant_id": "owner",
            "external_id": "loc-1",
            "name": "Office",
        },
        format="json",
        HTTP_X_PROVIDER_API_KEY="secret",
    )

    response = LocationUpsertView.as_view()(request)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "X-Idempotency-Key" in response.data["detail"]


@override_settings(B2B_TEST_API_KEY="secret")
def test_same_idempotency_key_and_same_payload_returns_cached_response(monkeypatch):
    manager = InMemoryIdempotencyManager()
    payload = {
        "source_owner_tenant_id": "owner",
        "external_id": "loc-1",
        "name": "Office",
    }

    monkeypatch.setattr(idempotency_service.transaction, "atomic", lambda: nullcontext())
    monkeypatch.setattr(idempotency_service, "B2BIdempotencyKey", SimpleNamespace(objects=manager))
    monkeypatch.setattr(
        inbound_service,
        "upsert_external_location",
        lambda **kwargs: (
            SimpleNamespace(
                external_id=kwargs["external_id"],
                source_owner_tenant_id=kwargs["source_owner_tenant_id"],
            ),
            True,
        ),
    )

    view = LocationUpsertView.as_view()
    first = view(
        APIRequestFactory().post(
            "/api/b2b/v1/locations/upsert/",
            payload,
            format="json",
            HTTP_X_PROVIDER_API_KEY="secret",
            HTTP_X_IDEMPOTENCY_KEY="idem-1",
        )
    )
    second = view(
        APIRequestFactory().post(
            "/api/b2b/v1/locations/upsert/",
            payload,
            format="json",
            HTTP_X_PROVIDER_API_KEY="secret",
            HTTP_X_IDEMPOTENCY_KEY="idem-1",
        )
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_201_CREATED
    assert second["X-Idempotent-Replay"] == "true"
    assert second.data == first.data


@override_settings(B2B_TEST_API_KEY="secret")
def test_same_idempotency_key_and_different_payload_returns_conflict(monkeypatch):
    manager = InMemoryIdempotencyManager()

    monkeypatch.setattr(idempotency_service.transaction, "atomic", lambda: nullcontext())
    monkeypatch.setattr(idempotency_service, "B2BIdempotencyKey", SimpleNamespace(objects=manager))
    monkeypatch.setattr(
        inbound_service,
        "upsert_external_location",
        lambda **kwargs: (
            SimpleNamespace(
                external_id=kwargs["external_id"],
                source_owner_tenant_id=kwargs["source_owner_tenant_id"],
            ),
            True,
        ),
    )

    view = LocationUpsertView.as_view()
    first = view(
        APIRequestFactory().post(
            "/api/b2b/v1/locations/upsert/",
            {
                "source_owner_tenant_id": "owner",
                "external_id": "loc-1",
                "name": "Office",
            },
            format="json",
            HTTP_X_PROVIDER_API_KEY="secret",
            HTTP_X_IDEMPOTENCY_KEY="idem-1",
        )
    )
    second = view(
        APIRequestFactory().post(
            "/api/b2b/v1/locations/upsert/",
            {
                "source_owner_tenant_id": "owner",
                "external_id": "loc-1",
                "name": "Different office",
            },
            format="json",
            HTTP_X_PROVIDER_API_KEY="secret",
            HTTP_X_IDEMPOTENCY_KEY="idem-1",
        )
    )

    assert first.status_code == status.HTTP_201_CREATED
    assert second.status_code == status.HTTP_409_CONFLICT


@override_settings(B2B_TEST_API_KEY="secret")
def test_telemetry_batch_endpoint_accepts_items_contract(monkeypatch):
    manager = InMemoryIdempotencyManager()
    captured = {}

    monkeypatch.setattr(idempotency_service.transaction, "atomic", lambda: nullcontext())
    monkeypatch.setattr(idempotency_service, "B2BIdempotencyKey", SimpleNamespace(objects=manager))

    def fake_ingest_telemetry_batch(*, source_owner_tenant_id, readings):
        captured["source_owner_tenant_id"] = source_owner_tenant_id
        captured["readings"] = readings
        return [SimpleNamespace()]

    monkeypatch.setattr(inbound_service, "ingest_telemetry_batch", fake_ingest_telemetry_batch)

    response = TelemetryBatchView.as_view()(
        APIRequestFactory().post(
            "/api/b2b/v1/telemetry/batch/",
            {
                "schema_version": "1.0",
                "source_owner_tenant_id": "owner",
                "items": [
                    {
                        "external_device_id": "device-1",
                        "external_reading_id": "reading-1",
                        "measured_at": "2026-05-11T10:05:00Z",
                        "temperature": 23.1,
                    }
                ],
            },
            format="json",
            HTTP_X_PROVIDER_API_KEY="secret",
            HTTP_X_IDEMPOTENCY_KEY="idem-telemetry-1",
        )
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert captured["source_owner_tenant_id"] == "owner"
    assert captured["readings"][0]["external_device_id"] == "device-1"
