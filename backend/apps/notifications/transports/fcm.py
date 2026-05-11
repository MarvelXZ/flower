"""FCM (Firebase Cloud Messaging) transport for push notification delivery.

Uses the ``firebase-admin`` SDK when available.  Falls back to a structured
log when the SDK is not installed (graceful degradation).
"""

import logging

from django.conf import settings

from apps.notifications.models import DevicePushToken
from apps.notifications.transports.base import NotificationTransportResponse

logger = logging.getLogger(__name__)


try:
    import firebase_admin
    from firebase_admin import credentials, messaging

    _FCM_AVAILABLE = True
except ImportError:
    _FCM_AVAILABLE = False
    firebase_admin = None
    credentials = None
    messaging = None


class FCMNotificationTransport:
    """Push notification transport for Firebase Cloud Messaging.

    Requires ``firebase-admin`` and a service account credentials file
    configured via ``FCM_CREDENTIALS_FILE``.

    The transport resolves active push tokens for the notification's
    recipient and sends a multicast message.
    """

    def __init__(self):
        self._initialized = False
        if _FCM_AVAILABLE:
            self._init_app()

    def _init_app(self):
        cred_path = getattr(settings, "FCM_CREDENTIALS_FILE", "")
        if cred_path and not firebase_admin._apps:
            try:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self._initialized = True
            except Exception:
                logger.exception("fcm_init_failed")

    def send(self, notification) -> NotificationTransportResponse:
        if not _FCM_AVAILABLE or not self._initialized:
            logger.info("fcm_not_available", extra={"notification_id": notification.pk})
            return NotificationTransportResponse(
                success=False, retryable=True,
                error="FCM SDK not available or not initialized.",
            )

        tokens = list(
            DevicePushToken.objects.filter(
                tenant_id=notification.recipient_id or "",
                is_active=True,
                provider_type="fcm",
            ).values_list("token", flat=True)
        )

        if not tokens:
            logger.info("fcm_no_tokens", extra={"notification_id": notification.pk})
            return NotificationTransportResponse(
                success=False, retryable=False,
                error="No active FCM tokens for recipient.",
            )

        payload = notification.payload or {}
        message = messaging.MulticastMessage(
            tokens=tokens,
            notification=messaging.Notification(
                title=payload.get("title", ""),
                body=payload.get("message", ""),
            ),
            data={
                "alert_id": str(payload.get("alert_id", "")),
                "notification_type": notification.notification_type,
                "severity": payload.get("severity", ""),
                "rule_code": payload.get("rule_code", ""),
            },
        )

        try:
            response = messaging.send_multicast(message)
            self._handle_invalid_tokens(response, tokens)
            if response.success_count > 0:
                return NotificationTransportResponse(
                    success=True,
                    provider_response={
                        "success_count": response.success_count,
                        "failure_count": response.failure_count,
                    },
                )
            return NotificationTransportResponse(
                success=False, retryable=True,
                error=f"FCM: all {response.failure_count} messages failed.",
            )
        except Exception as exc:
            logger.warning("fcm_send_error", extra={"error": str(exc)[:200]})
            return NotificationTransportResponse(
                success=False, retryable=True,
                error=f"FCM transport error: {exc}",
            )

    def _handle_invalid_tokens(self, response, tokens):
        """Deactivate tokens that returned an unrecoverable error."""
        if not messaging:
            return
        for idx, result in enumerate(response.responses):
            if result.exception and hasattr(result.exception, "code"):
                code = result.exception.code
                if code in ("UNREGISTERED", "INVALID_ARGUMENT", "NOT_FOUND"):
                    try:
                        DevicePushToken.objects.filter(token=tokens[idx]).update(is_active=False)
                    except Exception:
                        logger.warning("fcm_token_deactivation_failed")
