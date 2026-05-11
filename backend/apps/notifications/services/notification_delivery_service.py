"""Notification delivery service.

Dispatches a ``NotificationOutbox`` record through a replaceable transport
and updates its status based on the transport response.

Resolves the correct transport per channel:
- push  → ``FCMNotificationTransport``
- email → ``EmailNotificationTransport``
- otherwise → ``MockNotificationTransport`` (fallback)
"""

import logging


from apps.notifications.services.notification_outbox_service import (
    mark_dead_letter,
    mark_retry,
    mark_sent,
)
from apps.notifications.transports.email import EmailNotificationTransport
from apps.notifications.transports.fcm import FCMNotificationTransport
from apps.notifications.transports.mock import MockNotificationTransport

logger = logging.getLogger(__name__)


def _resolve_transport(channel: str):
    """Return the appropriate transport for a notification channel."""
    if channel == "push":
        return FCMNotificationTransport()
    if channel == "email":
        return EmailNotificationTransport()
    return MockNotificationTransport()


def deliver_notification(notification, transport=None) -> None:
    """Deliver one notification.

    If no transport is given, resolves the correct transport automatically
    based on ``notification.channel``.
    """
    channel = getattr(notification, "channel", "in_app")
    actual_transport = transport or _resolve_transport(channel)

    try:
        response = actual_transport.send(notification)
    except Exception as exc:
        _handle_error(notification, error=str(exc), retryable=True)
        return

    if response.success:
        mark_sent(notification, provider_response=response.provider_response)
        logger.info(
            "notification_sent",
            extra={
                "notification_id": notification.pk,
                "type": notification.notification_type,
                "channel": channel,
            },
        )
    elif response.retryable:
        _handle_error(notification, error=response.error, retryable=True)
    else:
        _handle_error(notification, error=response.error, retryable=False)


def _handle_error(notification, *, error: str, retryable: bool) -> None:
    logger.warning(
        "notification_delivery_failed",
        extra={
            "notification_id": notification.pk,
            "type": notification.notification_type,
            "channel": getattr(notification, "channel", "unknown"),
            "retryable": retryable,
            "error": error[:500],
        },
    )
    if retryable:
        mark_retry(notification, error=error)
    else:
        mark_dead_letter(notification, error=error)
