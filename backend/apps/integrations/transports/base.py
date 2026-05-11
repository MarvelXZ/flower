from dataclasses import dataclass, field
from typing import Protocol


class RetryableTransportError(RuntimeError):
    """Raised when transport failed before a definitive provider response."""


@dataclass(frozen=True)
class ProviderTransportResponse:
    status_code: int
    body: dict = field(default_factory=dict)
    error: str = ""
    retryable: bool = False
    duration_ms: int | None = None

    @property
    def success(self) -> bool:
        return 200 <= self.status_code < 300

    @property
    def permanent_failure(self) -> bool:
        return not self.success and not self.retryable and self.status_code < 500


class ProviderTransport(Protocol):
    def send(self, request):
        """Send a provider request and return ProviderTransportResponse."""
