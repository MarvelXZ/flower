"""Phase 6 tests for HTTP provider transport and HMAC signing."""

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework import exceptions, status
from rest_framework.test import APIRequestFactory

from apps.integrations.domain.enums import OutboxStatus, ProviderConnectionStatus, ProviderKeyStatus
from apps.integrations.services import outbox_delivery_service
from apps.integrations.services.hmac_signing_service import (
    HMAC_KEY_ID_HEADER,
    HMAC_SIGNATURE_HEADER,
    HMAC_TIMESTAMP_HEADER,
    IDEMPOTENCY_KEY_HEADER,
    build_canonical_string,
    build_hmac_headers,
    serialize_json_body,
)
from apps.integrations.services.outbox_delivery_service import deliver_outbox_event
from apps.integrations.transports.base import ProviderTransportResponse
from apps.integrations.transports.http import HttpProviderTransport
from apps.integrations.transports.mock import MockProviderTransport
from apps.provider_ops.api.authentication import B2BProviderAuthentication


@dataclass
class FakeEvent:
    event_type: str = "SensorReadingReceived"
    aggregate_type: str = "SensorReading"
    aggregate_id: str = "reading-1"
    status: str = OutboxStatus.PROCESSING
    idempotency_key: object = field(default_factory=uuid4)
    event_id: object = field(default_factory=uuid4)
    target_provider_schema: str = "provider"
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


def _active_connection():
    return SimpleNamespace(
        provider_tenant_id="provider",
        provider_base_url="https://provider.example.test",
        status=ProviderConnectionStatus.ACTIVE,
    )


def _http_transport(connection, handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpProviderTransport(connection=connection, client=client, timeout_seconds=0.1)


def _patch_delivery(monkeypatch, connection, secret="shared-secret"):
    monkeypatch.setattr(
        outbox_delivery_service,
        "get_active_provider_connections_for_event",
        lambda event: [connection],
    )
    monkeypatch.setattr(
        outbox_delivery_service,
        "get_active_key_for_connection",
        lambda *, provider_connection: SimpleNamespace(
            key_id="key-1",
            secret_reference="secret://provider/key-1",
        ),
    )
    monkeypatch.setattr(
        outbox_delivery_service,
        "resolve_secret",
        lambda secret_reference, resolver=None: secret,
    )
    monkeypatch.setattr(outbox_delivery_service, "record_delivery_attempt", lambda *args, **kwargs: None)


def _django_hmac_headers(headers):
    return {
        "HTTP_X_B2B_TIMESTAMP": headers[HMAC_TIMESTAMP_HEADER],
        "HTTP_X_B2B_SIGNATURE": headers[HMAC_SIGNATURE_HEADER],
        "HTTP_X_B2B_KEY_ID": headers[HMAC_KEY_ID_HEADER],
        "HTTP_X_IDEMPOTENCY_KEY": headers[IDEMPOTENCY_KEY_HEADER],
    }


def test_hmac_signature_is_deterministic():
    body = serialize_json_body({"b": 2, "a": 1})
    headers = build_hmac_headers(
        method="POST",
        path="/api/b2b/v1/telemetry/batch/",
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1234567890,
    )
    canonical = build_canonical_string(
        method="POST",
        path="/api/b2b/v1/telemetry/batch/",
        timestamp="1234567890",
        idempotency_key="idem-1",
        body_sha256=hashlib.sha256(body).hexdigest(),
    )
    expected = hmac.new(b"secret", canonical.encode("utf-8"), hashlib.sha256).hexdigest()

    assert headers[HMAC_SIGNATURE_HEADER] == expected
    assert headers[HMAC_SIGNATURE_HEADER] == build_hmac_headers(
        method="POST",
        path="/api/b2b/v1/telemetry/batch/",
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1234567890,
    )[HMAC_SIGNATURE_HEADER]


@override_settings(
    B2B_TEST_KEY_ID="key-1",
    B2B_TEST_SHARED_SECRET="secret",
    B2B_HMAC_MAX_SKEW_SECONDS=300,
)
def test_valid_hmac_allows_provider_auth():
    path = "/api/b2b/v1/telemetry/batch/"
    body = b'{"schema_version":"1.0"}'
    headers = build_hmac_headers(
        method="POST",
        path=path,
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1_800_000_000,
    )
    request = APIRequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        **_django_hmac_headers(headers),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("apps.integrations.services.hmac_signing_service.time.time", lambda: 1_800_000_000)
        principal, auth = B2BProviderAuthentication().authenticate(request)

    assert principal.is_authenticated is True
    assert auth is None


@override_settings(
    B2B_TEST_KEY_ID="key-1",
    B2B_TEST_SHARED_SECRET="secret",
    B2B_HMAC_MAX_SKEW_SECONDS=300,
)
def test_invalid_hmac_is_rejected():
    path = "/api/b2b/v1/telemetry/batch/"
    body = b'{"schema_version":"1.0"}'
    headers = build_hmac_headers(
        method="POST",
        path=path,
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1_800_000_000,
    )
    headers[HMAC_SIGNATURE_HEADER] = "bad-signature"
    request = APIRequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        **_django_hmac_headers(headers),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("apps.integrations.services.hmac_signing_service.time.time", lambda: 1_800_000_000)
        with pytest.raises(exceptions.AuthenticationFailed):
            B2BProviderAuthentication().authenticate(request)


@override_settings(
    B2B_TEST_KEY_ID="key-1",
    B2B_TEST_SHARED_SECRET="secret",
    B2B_HMAC_MAX_SKEW_SECONDS=300,
)
def test_expired_hmac_timestamp_is_rejected():
    path = "/api/b2b/v1/telemetry/batch/"
    body = b'{"schema_version":"1.0"}'
    headers = build_hmac_headers(
        method="POST",
        path=path,
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1_799_999_000,
    )
    request = APIRequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        **_django_hmac_headers(headers),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("apps.integrations.services.hmac_signing_service.time.time", lambda: 1_800_000_000)
        with pytest.raises(exceptions.AuthenticationFailed):
            B2BProviderAuthentication().authenticate(request)


@override_settings(
    B2B_TEST_KEY_ID="key-1",
    B2B_TEST_SHARED_SECRET="secret",
    B2B_HMAC_MAX_SKEW_SECONDS=300,
)
def test_invalid_key_id_is_rejected():
    path = "/api/b2b/v1/telemetry/batch/"
    body = b'{"schema_version":"1.0"}'
    headers = build_hmac_headers(
        method="POST",
        path=path,
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="unknown-key",
        shared_secret="secret",
        timestamp=1_800_000_000,
    )
    request = APIRequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        **_django_hmac_headers(headers),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("apps.integrations.services.hmac_signing_service.time.time", lambda: 1_800_000_000)
        with pytest.raises(exceptions.AuthenticationFailed):
            B2BProviderAuthentication().authenticate(request)


@override_settings(
    B2B_TEST_KEY_ID="key-1",
    B2B_TEST_SHARED_SECRET="secret",
    B2B_TEST_KEY_STATUS=ProviderKeyStatus.REVOKED,
    B2B_HMAC_MAX_SKEW_SECONDS=300,
)
def test_revoked_inbound_key_is_rejected():
    path = "/api/b2b/v1/telemetry/batch/"
    body = b'{"schema_version":"1.0"}'
    headers = build_hmac_headers(
        method="POST",
        path=path,
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1_800_000_000,
    )
    request = APIRequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        **_django_hmac_headers(headers),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("apps.integrations.services.hmac_signing_service.time.time", lambda: 1_800_000_000)
        with pytest.raises(exceptions.AuthenticationFailed):
            B2BProviderAuthentication().authenticate(request)


@override_settings(
    B2B_TEST_KEY_ID="key-1",
    B2B_TEST_SHARED_SECRET="secret",
    B2B_TEST_KEY_VALID_UNTIL=timezone.now() - timedelta(seconds=1),
    B2B_HMAC_MAX_SKEW_SECONDS=300,
)
def test_expired_inbound_key_is_rejected():
    path = "/api/b2b/v1/telemetry/batch/"
    body = b'{"schema_version":"1.0"}'
    headers = build_hmac_headers(
        method="POST",
        path=path,
        body_bytes=body,
        idempotency_key="idem-1",
        key_id="key-1",
        shared_secret="secret",
        timestamp=1_800_000_000,
    )
    request = APIRequestFactory().post(
        path,
        data=body,
        content_type="application/json",
        **_django_hmac_headers(headers),
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr("apps.integrations.services.hmac_signing_service.time.time", lambda: 1_800_000_000)
        with pytest.raises(exceptions.AuthenticationFailed):
            B2BProviderAuthentication().authenticate(request)


def test_active_provider_key_is_used_for_signing(monkeypatch):
    event = FakeEvent()
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection, secret="active-secret")
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=202))

    deliver_outbox_event(event, transport)

    signed_request = transport.sent_requests[0]
    expected = build_hmac_headers(
        method=signed_request.method,
        path=signed_request.endpoint,
        body_bytes=signed_request.body_bytes,
        idempotency_key=signed_request.idempotency_key,
        key_id="key-1",
        shared_secret="active-secret",
        timestamp=signed_request.headers[HMAC_TIMESTAMP_HEADER],
    )
    assert signed_request.headers[HMAC_KEY_ID_HEADER] == "key-1"
    assert signed_request.headers[HMAC_SIGNATURE_HEADER] == expected[HMAC_SIGNATURE_HEADER]


def test_http_2xx_marks_event_processed(monkeypatch):
    event = FakeEvent()
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection)
    transport = _http_transport(connection, lambda request: httpx.Response(status.HTTP_202_ACCEPTED, json={"ok": True}))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.PROCESSED
    assert event.processed_at is not None


def test_http_timeout_marks_event_retry(monkeypatch):
    event = FakeEvent()
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection)

    def raise_timeout(request):
        raise httpx.TimeoutException("timed out")

    deliver_outbox_event(event, _http_transport(connection, raise_timeout))

    assert event.status == OutboxStatus.RETRY
    assert event.last_error == "Provider HTTP request timed out."


@pytest.mark.parametrize("status_code", [status.HTTP_429_TOO_MANY_REQUESTS, status.HTTP_500_INTERNAL_SERVER_ERROR])
def test_http_retryable_status_marks_event_retry(monkeypatch, status_code):
    event = FakeEvent()
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection)
    transport = _http_transport(connection, lambda request: httpx.Response(status_code, json={"ok": False}))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.RETRY


@pytest.mark.parametrize("status_code", [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])
def test_http_permanent_status_marks_event_dead_letter(monkeypatch, status_code):
    event = FakeEvent()
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection)
    transport = _http_transport(connection, lambda request: httpx.Response(status_code, json={"ok": False}))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.DEAD_LETTER


def test_secret_is_not_written_to_delivery_logs(monkeypatch, caplog):
    event = FakeEvent()
    secret = "super-secret-never-log"
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection, secret=secret)
    transport = _http_transport(
        connection,
        lambda request: httpx.Response(status.HTTP_500_INTERNAL_SERVER_ERROR, json={"ok": False}),
    )

    caplog.set_level(logging.INFO, logger="apps.integrations.services.outbox_delivery_service")
    deliver_outbox_event(event, transport)

    assert secret not in caplog.text


def test_mock_transport_still_works(monkeypatch):
    event = FakeEvent()
    connection = _active_connection()
    _patch_delivery(monkeypatch, connection)
    transport = MockProviderTransport(response=ProviderTransportResponse(status_code=202))

    deliver_outbox_event(event, transport)

    assert event.status == OutboxStatus.PROCESSED
    assert transport.sent_requests[0].headers[HMAC_SIGNATURE_HEADER]
