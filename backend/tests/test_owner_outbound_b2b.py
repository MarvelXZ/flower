"""Phase 5 tests for owner outbound B2B client skeleton."""

from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

from django.utils import timezone

from apps.integrations.domain.constants import MAX_RETRY_COUNT
from apps.integrations.domain.enums import OutboxStatus, ProviderConnectionStatus
from apps.integrations.services.b2b_payload_mapper import map_outbox_event_to_provider_request
from apps.integrations.services.outbox_delivery_service import deliver_outbox_event
from apps.integrations.services import outbox_delivery_service
from apps.integrations.tasks import outbox_tasks
from apps.integrations.transports.base import ProviderTransportResponse, RetryableTransportError
from apps.integrations.transports.mock import MockProviderTransport


@dataclass
class FakeEvent:
    event_type: str = "SensorReadingReceived"
    aggregate_type: str = "SensorReading"
    aggregate_id: str = "reading-1"
    status: str = OutboxStatus.PROCESSING
    idempotency_key: object = field(default_factory=uuid4)
    event_id: object = field(default_factory=uuid4)
    target_provider_schema: str = ""
    retry_count: int = 0
    attempts: int = 0
    last_error: str = ""
    processed_at: object | None = None
    available_at: object = field(default_factory=timezone.now)
    saved_update_fields: list[str] | None = None
    payload: dict = field(
        default_factory=lambda: {
            "source_owner_tenant_id": "owner",
            "sensor_reading_id": "reading-1",
            "device_uuid": "device-1",
            "measured_at": "2026-05-11T10:05:00+00:00",
            "soil_moisture": 42.5,
            "temperature": 23.1,
            "air_humidity": 55.0,
            "light_level": 300,
            "battery_level": 87,
        }
    )

    def save(self, *, update_fields):
        self.saved_update_fields = list(update_fields)


def _active_connection(provider_tenant_id="provider"):
    return SimpleNamespace(
        provider_tenant_id=provider_tenant_id,
        provider_base_url="https://provider.example.test",
        status=ProviderConnectionStatus.ACTIVE,
    )


def _active_key():
    return SimpleNamespace(key_id="key-1", secret_reference="secret://provider/key-1")


def _patch_provider_key(monkeypatch):
    monkeypatch.setattr(
        outbox_delivery_service,
        "get_active_key_for_connection",
        lambda *, provider_connection: _active_key(),
    )
    monkeypatch.setattr(
        outbox_delivery_service,
        "resolve_secret",
        lambda secret_reference, resolver=None: "shared-secret",
    )


def test_sensor_reading_received_maps_to_telemetry_batch_contract():
    event = FakeEvent()

    request = map_outbox_event_to_provider_request(event)

    assert request.method == "POST"
    assert request.endpoint == "/api/b2b/v1/telemetry/batch/"
    assert request.payload["schema_version"] == "1.0"
    assert request.payload["source_owner_tenant_id"] == "owner"
    assert request.payload["items"][0]["external_reading_id"] == "reading-1"
    assert request.payload["items"][0]["external_device_id"] == "device-1"
    assert request.payload["items"][0]["temperature"] == 23.1


def test_mapper_idempotency_key_is_stable_for_same_event():
    event = FakeEvent()

    first = map_outbox_event_to_provider_request(event)
    second = map_outbox_event_to_provider_request(event)

    assert first.idempotency_key == second.idempotency_key


def test_successful_mock_transport_marks_event_processed(monkeypatch):
    event = FakeEvent()
    attempts = []
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=202))

    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [_active_connection()])
    _patch_provider_key(monkeypatch)
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: attempts.append((args, kwargs)))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.PROCESSED
    assert event.processed_at is not None
    assert attempts[0][0][1] == OutboxStatus.PROCESSED
    assert transport.sent_requests[0].idempotency_key == str(event.idempotency_key)


def test_retryable_mock_failure_marks_event_retry(monkeypatch):
    event = FakeEvent()
    attempts = []
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=503, retryable=True, error="unavailable"))

    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [_active_connection()])
    _patch_provider_key(monkeypatch)
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: attempts.append((args, kwargs)))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.RETRY
    assert event.retry_count == 1
    assert event.last_error == "unavailable"
    assert attempts[0][0][1] == OutboxStatus.RETRY


def test_retryable_transport_exception_marks_event_retry(monkeypatch):
    event = FakeEvent()
    transport = MockProviderTransport(exc=RetryableTransportError("network unavailable"))

    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [_active_connection()])
    _patch_provider_key(monkeypatch)
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: None)

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.RETRY
    assert event.last_error == "network unavailable"


def test_permanent_mock_failure_marks_event_dead_letter(monkeypatch):
    event = FakeEvent()
    attempts = []
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=400, error="bad contract"))

    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [_active_connection()])
    _patch_provider_key(monkeypatch)
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: attempts.append((args, kwargs)))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.DEAD_LETTER
    assert event.retry_count == 1
    assert event.last_error == "bad contract"
    assert attempts[0][0][1] == OutboxStatus.DEAD_LETTER


def test_failure_after_max_retries_marks_dead_letter(monkeypatch):
    event = FakeEvent(retry_count=MAX_RETRY_COUNT - 1)
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=503, retryable=True, error="unavailable"))

    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [_active_connection()])
    _patch_provider_key(monkeypatch)
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: None)

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.DEAD_LETTER
    assert event.retry_count == MAX_RETRY_COUNT


def test_no_active_provider_connection_marks_retry(monkeypatch):
    event = FakeEvent()

    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [])
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: None)

    deliver_outbox_event(event, MockProviderTransport())

    assert event.status == OutboxStatus.RETRY
    assert event.last_error == "No active provider connection for outbox event."


def test_revoked_provider_connection_is_not_used(monkeypatch):
    event = FakeEvent()
    revoked_connection = SimpleNamespace(
        provider_tenant_id="provider",
        status=ProviderConnectionStatus.REVOKED,
    )

    monkeypatch.setattr(
        outbox_delivery_service,
        "get_active_provider_connections_for_event",
        lambda event: [] if revoked_connection.status == ProviderConnectionStatus.REVOKED else [revoked_connection],
    )
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: None)

    deliver_outbox_event(event, MockProviderTransport())

    assert event.status == OutboxStatus.RETRY


def test_task_processes_batch_through_mock_transport(monkeypatch):
    event = FakeEvent()
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=202))

    monkeypatch.setattr(outbox_tasks, "claim_pending_events", lambda limit: [event])
    monkeypatch.setattr(outbox_delivery_service, "get_active_provider_connections_for_event", lambda event: [_active_connection()])
    _patch_provider_key(monkeypatch)
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: None)

    result = outbox_tasks.process_integration_outbox_batch_impl(limit=10, transport=transport)

    assert result == {"claimed": 1, "processed": 1, "retry": 0, "dead_letter": 0}
    assert event.status == OutboxStatus.PROCESSED
