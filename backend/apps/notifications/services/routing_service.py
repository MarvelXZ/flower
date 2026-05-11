"""Notification routing and channel resolution service.

Determines which channels a notification should be sent over based on
alert severity, notification type, and recipient preferences.
"""

from apps.notifications.domain.enums import NotificationChannel
from apps.notifications.models import DevicePushToken, EmailDestination, NotificationPreference

_SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def resolve_channels(*, severity: str) -> list[str]:
    """Return the list of channels to use for a given alert severity.

    Default routing (before preference overrides):
    - critical → push + email
    - warning  → push
    - info     → in_app
    """
    if severity == "critical":
        return [NotificationChannel.PUSH, NotificationChannel.EMAIL]
    if severity == "warning":
        return [NotificationChannel.PUSH]
    return [NotificationChannel.IN_APP]


def resolve_push_tokens(*, tenant_id: str) -> list[str]:
    """Return active FCM push tokens for a tenant."""
    return list(
        DevicePushToken.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            provider_type="fcm",
        ).values_list("token", flat=True)
    )


def resolve_email_destinations(*, tenant_id: str) -> list[str]:
    """Return active verified email addresses for a tenant."""
    return list(
        EmailDestination.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
            is_verified=True,
        ).values_list("email", flat=True)
    )


def check_preferences_allows(
    *, recipient_type: str, recipient_id: str, channel: str, severity: str,
) -> bool:
    """Check whether notification preferences allow delivery.

    If no explicit preference exists, delivery is allowed (opt-out model).
    If a preference exists and is ``enabled=False``, delivery is blocked.
    If a preference has a higher ``alert_severity_min`` than the alert's
    severity, delivery is blocked.
    """
    pref = NotificationPreference.objects.filter(
        recipient_type=recipient_type,
        recipient_id=recipient_id,
        channel=channel,
    ).first()

    if pref is None:
        return True  # opt-out: no preference = allowed

    if not pref.enabled:
        return False

    min_sev = _SEVERITY_ORDER.get(pref.alert_severity_min, 0)
    actual_sev = _SEVERITY_ORDER.get(severity, 0)
    return actual_sev >= min_sev
