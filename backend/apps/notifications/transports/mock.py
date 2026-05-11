"""Mock notification transport for testing.

Supports three modes:
- ``success`` — always succeeds
- ``retryable`` — always returns a retryable error
- ``permanent`` — always returns a permanent failure
"""

from apps.notifications.transports.base import NotificationTransportResponse


class MockNotificationTransport:
    """Mock transport with configurable behaviour."""

    def __init__(self, mode: str = "success"):
        self.mode = mode

    def send(self, notification) -> NotificationTransportResponse:
        if self.mode == "success":
            return NotificationTransportResponse(
                success=True,
                provider_response={"mock_id": "mock-001"},
            )
        if self.mode == "retryable":
            return NotificationTransportResponse(
                success=False,
                retryable=True,
                error="Mock retryable transport error.",
            )
        if self.mode == "permanent":
            return NotificationTransportResponse(
                success=False,
                retryable=False,
                error="Mock permanent transport error.",
            )
        return NotificationTransportResponse(success=True)
