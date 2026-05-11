from apps.integrations.transports.base import ProviderTransportResponse, RetryableTransportError


class MockProviderTransport:
    """In-memory provider transport used before real HTTP delivery exists."""

    def __init__(self, *, response: ProviderTransportResponse | None = None, exc: Exception | None = None):
        self.response = response or ProviderTransportResponse(status_code=202, body={"status": "accepted"})
        self.exc = exc
        self.sent_requests = []

    def send(self, request):
        self.sent_requests.append(request)
        if self.exc:
            raise self.exc
        return self.response


__all__ = ["MockProviderTransport", "ProviderTransportResponse", "RetryableTransportError"]
