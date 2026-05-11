"""Replaceable transport interface for notification delivery."""

from dataclasses import dataclass, field
from typing import Protocol

from apps.notifications.models import NotificationOutbox


class RetryableTransportError(RuntimeError):
    """Raised when a transport failure is retryable."""


@dataclass(frozen=True)
class NotificationTransportResponse:
    success: bool = True
    retryable: bool = False
    error: str = ""
    provider_response: dict = field(default_factory=dict)


class NotificationTransport(Protocol):
    def send(self, notification: NotificationOutbox) -> NotificationTransportResponse:
        """Deliver a notification and return a response."""
