import logging

from apps.integrations.domain.constants import DEFAULT_RETRY_DELAY_SECONDS, MAX_RETRY_COUNT
from apps.integrations.domain.enums import OutboxStatus
from apps.integrations.services.b2b_payload_mapper import map_outbox_event_to_provider_request
from apps.integrations.services.hmac_signing_service import sign_provider_request
from apps.integrations.services.outbox_service import (
    mark_dead_letter,
    mark_processed,
    mark_retry,
    record_delivery_attempt,
)
from apps.integrations.services.provider_connection_service import (
    get_active_provider_connections_for_event,
)
from apps.integrations.services.provider_key_service import (
    ProviderKeyUnavailable,
    get_active_key_for_connection,
)
from apps.integrations.services.secret_resolver import SecretNotFound, resolve_secret
from apps.integrations.transports.base import RetryableTransportError
from apps.integrations.transports.http import HttpProviderTransport


logger = logging.getLogger(__name__)


class NoActiveProviderConnection(RuntimeError):
    """Raised internally when no active provider connection can receive an event."""


def _mark_failure(event, *, error: str, retryable: bool, response_code=None):
    if retryable and event.retry_count + 1 < MAX_RETRY_COUNT:
        record_delivery_attempt(
            event,
            OutboxStatus.RETRY,
            error=error,
            response_code=response_code,
        )
        return mark_retry(
            event,
            error=error,
            retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
        )

    record_delivery_attempt(
        event,
        OutboxStatus.DEAD_LETTER,
        error=error,
        response_code=response_code,
    )
    return mark_dead_letter(event, error=error)


def _log_delivery_result(event, connection, request, response):
    logger.info(
        "provider_b2b_delivery_result",
        extra={
            "event_id": str(getattr(event, "event_id", "")),
            "event_type": getattr(event, "event_type", ""),
            "provider_tenant_id": getattr(connection, "provider_tenant_id", ""),
            "endpoint": request.endpoint,
            "status_code": response.status_code,
            "retryable": response.retryable,
            "permanent": response.permanent_failure,
            "duration_ms": response.duration_ms,
        },
    )


def deliver_outbox_event(event, transport=None, secret_resolver=None):
    """Deliver one processing outbox event through a replaceable transport."""
    connections = list(get_active_provider_connections_for_event(event))
    if not connections:
        return _mark_failure(
            event,
            error="No active provider connection for outbox event.",
            retryable=True,
        )

    connection = connections[0]
    request = map_outbox_event_to_provider_request(event)
    try:
        provider_key = get_active_key_for_connection(provider_connection=connection)
        shared_secret = resolve_secret(
            provider_key.secret_reference,
            resolver=secret_resolver,
        )
    except (ProviderKeyUnavailable, SecretNotFound) as exc:
        return _mark_failure(event, error=str(exc), retryable=True)

    request = sign_provider_request(
        request,
        key_id=provider_key.key_id,
        shared_secret=shared_secret,
    )
    provider_transport = transport or HttpProviderTransport(connection=connection)

    try:
        response = provider_transport.send(request)
    except RetryableTransportError as exc:
        return _mark_failure(event, error=str(exc), retryable=True)

    _log_delivery_result(event, connection, request, response)

    if response.success:
        record_delivery_attempt(
            event,
            OutboxStatus.PROCESSED,
            response_code=response.status_code,
        )
        return mark_processed(event)

    error = response.error or f"Provider transport returned status {response.status_code}."
    return _mark_failure(
        event,
        error=error,
        retryable=response.retryable or response.status_code >= 500,
        response_code=response.status_code,
    )
