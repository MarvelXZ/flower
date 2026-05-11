import time

import httpx
from django.conf import settings

from apps.integrations.services.hmac_signing_service import serialize_json_body
from apps.integrations.transports.base import ProviderTransportResponse, RetryableTransportError


RETRYABLE_STATUS_CODES = {429}
PERMANENT_STATUS_CODES = {400, 401, 403, 404, 409, 422}


class HttpProviderTransport:
    """HTTP implementation of the provider transport interface."""

    def __init__(self, *, connection, client=None, timeout_seconds: float | None = None):
        self.connection = connection
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else getattr(settings, "B2B_HTTP_TIMEOUT_SECONDS", 5.0)
        )
        self.client = client or httpx.Client(timeout=self.timeout_seconds)

    def send(self, request) -> ProviderTransportResponse:
        url = self._build_url(request.endpoint)
        body_bytes = request.body_bytes or serialize_json_body(request.payload)
        headers = {"Content-Type": "application/json", **request.headers}
        started_at = time.perf_counter()

        try:
            response = self.client.request(
                request.method,
                url,
                content=body_bytes,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise RetryableTransportError("Provider HTTP request timed out.") from exc
        except httpx.TransportError as exc:
            raise RetryableTransportError("Provider HTTP request failed before response.") from exc

        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return ProviderTransportResponse(
            status_code=response.status_code,
            body=self._response_body(response),
            error=self._response_error(response),
            retryable=self._is_retryable_status(response.status_code),
            duration_ms=duration_ms,
        )

    def _build_url(self, endpoint: str) -> str:
        base_url = str(self.connection.provider_base_url).rstrip("/")
        return f"{base_url}/{endpoint.lstrip('/')}"

    def _response_body(self, response: httpx.Response) -> dict:
        try:
            parsed = response.json()
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {"data": parsed}

    def _response_error(self, response: httpx.Response) -> str:
        if 200 <= response.status_code < 300:
            return ""
        if response.status_code == 409:
            return "Provider idempotency conflict."
        if response.status_code in PERMANENT_STATUS_CODES:
            return f"Provider returned permanent status {response.status_code}."
        if self._is_retryable_status(response.status_code):
            return f"Provider returned retryable status {response.status_code}."
        return f"Provider returned status {response.status_code}."

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code in RETRYABLE_STATUS_CODES or 500 <= status_code <= 599
