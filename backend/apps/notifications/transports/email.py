"""SMTP email transport for notification delivery.

Uses Django's built-in ``send_mail`` with a configurable timeout.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.models import EmailDestination
from apps.notifications.transports.base import (
    NotificationTransportResponse,
)

logger = logging.getLogger(__name__)


class EmailNotificationTransport:
    """Email transport backed by Django's SMTP email backend.

    Resolves active email destinations for the notification's recipient
    tenant and sends a plain-text email.
    """

    def send(self, notification) -> NotificationTransportResponse:
        if not getattr(settings, "EMAIL_ENABLED", False):
            logger.info("email_not_enabled", extra={"notification_id": notification.pk})
            return NotificationTransportResponse(
                success=False, retryable=True,
                error="Email delivery is not enabled (EMAIL_ENABLED=False).",
            )

        emails = list(
            EmailDestination.objects.filter(
                tenant_id=notification.recipient_id or "",
                is_active=True,
                is_verified=True,
            ).values_list("email", flat=True)
        )

        if not emails:
            logger.info("email_no_destinations", extra={"notification_id": notification.pk})
            return NotificationTransportResponse(
                success=False, retryable=False,
                error="No active email destinations for recipient.",
            )

        payload = notification.payload or {}
        subject = f"[Flower] {payload.get('title', 'Notification')}"
        message = self._build_body(payload)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@flower.local")
        timeout = getattr(settings, "EMAIL_TIMEOUT_SECONDS", 10)

        try:
            sent = send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=emails,
                fail_silently=False,
                timeout=timeout,
            )
            if sent == 1:
                return NotificationTransportResponse(
                    success=True,
                    provider_response={"recipient_count": len(emails)},
                )
            return NotificationTransportResponse(
                success=False, retryable=True,
                error="SMTP returned non-success.",
            )
        except Exception as exc:
            error_str = str(exc)[:300]
            logger.warning("email_send_error", extra={"error": error_str})
            return NotificationTransportResponse(
                success=False, retryable=True,
                error=f"SMTP error: {error_str}",
            )

    def _build_body(self, payload: dict) -> str:
        lines = [
            payload.get("title", ""),
            "",
            payload.get("message", ""),
            "",
        ]
        severity = payload.get("severity", "")
        rule_code = payload.get("rule_code", "")
        alert_id = payload.get("alert_id", "")
        if severity:
            lines.append(f"Severity: {severity}")
        if rule_code:
            lines.append(f"Rule: {rule_code}")
        if alert_id:
            lines.append(f"Alert ID: {alert_id}")
        lines.append("")
        lines.append("---")
        lines.append("Flower Notification System")
        return "\n".join(lines)
