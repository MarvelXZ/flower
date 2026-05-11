"""Celery tasks for the notification outbox delivery pipeline."""

from celery import shared_task

from apps.notifications.services.notification_delivery_service import deliver_notification
from apps.notifications.services.notification_outbox_service import claim_pending_notifications


def _process_batch(notifications, transport=None) -> dict:
    """Deliver a list of notifications and return a summary dict."""
    result = {
        "claimed": len(notifications),
        "sent": 0,
        "retry": 0,
        "dead_letter": 0,
    }

    for notification in notifications:
        deliver_notification(notification, transport)
        if notification.status == "sent":
            result["sent"] += 1
        elif notification.status == "retry":
            result["retry"] += 1
        elif notification.status in ("failed", "dead_letter"):
            result["dead_letter"] += 1

    return result


@shared_task(name="notifications.process_notification_outbox_batch")
def process_notification_outbox_batch(limit: int = 100) -> dict:
    """Claim and deliver a batch of pending notifications.

    Transport is auto-resolved per notification by ``deliver_notification``
    based on ``notification.channel``.
    """
    notifications = claim_pending_notifications(limit=limit)
    return _process_batch(notifications)


@shared_task(name="notifications.process_push_notifications_batch")
def process_push_notifications_batch(limit: int = 100) -> dict:
    """Claim and deliver push notifications only."""
    notifications = claim_pending_notifications(limit=limit)
    push_only = [n for n in notifications if n.channel == "push"]
    return _process_batch(push_only)


@shared_task(name="notifications.process_email_notifications_batch")
def process_email_notifications_batch(limit: int = 100) -> dict:
    """Claim and deliver email notifications only."""
    notifications = claim_pending_notifications(limit=limit)
    email_only = [n for n in notifications if n.channel == "email"]
    return _process_batch(email_only)

