"""Unit tests for Phase 13: real notification providers."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from apps.notifications.domain.enums import NotificationChannel
from apps.notifications.services.routing_service import (
    check_preferences_allows,
    resolve_channels,
)
from apps.notifications.transports.email import EmailNotificationTransport
from apps.notifications.transports.fcm import FCMNotificationTransport
from apps.notifications.transports.mock import MockNotificationTransport


# ============================================================================
# Helpers
# ============================================================================

def _make_notification(channel=NotificationChannel.IN_APP, **kw):
    defaults = {
        "pk": 1, "notification_type": "alert_created", "channel": channel,
        "recipient_type": "tenant", "recipient_id": "tenant-1",
        "payload": {"title": "Test", "message": "Body", "severity": "warning",
                     "alert_id": "1", "rule_code": "test_rule"},
        "status": "pending", "attempt_count": 0,
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ============================================================================
# 1. Routing
# ============================================================================


def test_critical_routes_push_and_email():
    channels = resolve_channels(severity="critical")
    assert NotificationChannel.PUSH in channels
    assert NotificationChannel.EMAIL in channels


def test_warning_routes_push_only():
    channels = resolve_channels(severity="warning")
    assert NotificationChannel.PUSH in channels
    assert NotificationChannel.EMAIL not in channels


def test_info_routes_in_app():
    channels = resolve_channels(severity="info")
    assert channels == [NotificationChannel.IN_APP]


def test_check_preferences_no_pref_allowed(monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.services.routing_service.NotificationPreference",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=None)))
            )
        ),
    )
    assert check_preferences_allows(recipient_type="tenant", recipient_id="t1", channel="push", severity="warning") is True


def test_check_preferences_disabled_blocks(monkeypatch):
    pref = SimpleNamespace(enabled=False, alert_severity_min="info")
    monkeypatch.setattr(
        "apps.notifications.services.routing_service.NotificationPreference",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=pref)))
            )
        ),
    )
    assert check_preferences_allows(recipient_type="tenant", recipient_id="t1", channel="push", severity="warning") is False


def test_check_preferences_severity_too_low_blocks(monkeypatch):
    pref = SimpleNamespace(enabled=True, alert_severity_min="critical")
    monkeypatch.setattr(
        "apps.notifications.services.routing_service.NotificationPreference",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=pref)))
            )
        ),
    )
    # Warning < critical, so should be blocked
    assert check_preferences_allows(recipient_type="tenant", recipient_id="t1", channel="push", severity="warning") is False


def test_check_preferences_severity_meets_threshold(monkeypatch):
    pref = SimpleNamespace(enabled=True, alert_severity_min="warning")
    monkeypatch.setattr(
        "apps.notifications.services.routing_service.NotificationPreference",
        SimpleNamespace(
            objects=SimpleNamespace(
                filter=MagicMock(return_value=SimpleNamespace(first=MagicMock(return_value=pref)))
            )
        ),
    )
    assert check_preferences_allows(recipient_type="tenant", recipient_id="t1", channel="push", severity="critical") is True


# ============================================================================
# 2. Mock transport (regression check)
# ============================================================================


def test_mock_success():
    t = MockNotificationTransport(mode="success")
    r = t.send(_make_notification())
    assert r.success is True


def test_mock_retryable():
    t = MockNotificationTransport(mode="retryable")
    r = t.send(_make_notification())
    assert r.success is False
    assert r.retryable is True


def test_mock_permanent():
    t = MockNotificationTransport(mode="permanent")
    r = t.send(_make_notification())
    assert r.success is False
    assert r.retryable is False


# ============================================================================
# 3. FCM transport (SDK simulation)
# ============================================================================


def test_fcm_no_sdk_fallback():
    """When FCM SDK is unavailable, returns retryable error."""
    t = FCMNotificationTransport()
    t._initialized = False
    n = _make_notification(channel="push")
    r = t.send(n)
    assert r.success is False
    assert r.retryable is True


@patch("apps.notifications.transports.fcm._FCM_AVAILABLE", True)
@patch("apps.notifications.transports.fcm.firebase_admin", MagicMock())
@patch("apps.notifications.transports.fcm.messaging", MagicMock())
def test_fcm_no_tokens(monkeypatch):
    """With no active tokens, FCM returns permanent error."""
    class FakeTokenQS:
        def filter(self, **kw):
            return self
        def values_list(self, *a, **kw):
            return []
    monkeypatch.setattr(
        "apps.notifications.transports.fcm.DevicePushToken",
        SimpleNamespace(objects=FakeTokenQS()),
    )
    monkeypatch.setattr(
        "apps.notifications.transports.fcm.settings",
        SimpleNamespace(FCM_CREDENTIALS_FILE="/fake/path.json"),
    )

    # Mock firebase_admin._apps to avoid init
    import apps.notifications.transports.fcm as fcm_mod
    fcm_mod.firebase_admin._apps = MagicMock()

    t = FCMNotificationTransport()
    t._initialized = True
    n = _make_notification(channel="push", recipient_id="tenant-no-tokens")
    r = t.send(n)
    assert r.success is False
    # No active tokens = permanent
    assert r.retryable is False


# ============================================================================
# 4. Email transport
# ============================================================================


def test_email_not_enabled(monkeypatch):
    """When EMAIL_ENABLED=False, returns retryable."""
    monkeypatch.setattr(
        "apps.notifications.transports.email.settings",
        SimpleNamespace(EMAIL_ENABLED=False),
    )
    t = EmailNotificationTransport()
    n = _make_notification(channel="email")
    r = t.send(n)
    assert r.success is False
    assert r.retryable is True


def test_email_no_destinations(monkeypatch):
    """With no active destinations, returns permanent error."""
    monkeypatch.setattr(
        "apps.notifications.transports.email.settings",
        SimpleNamespace(
            EMAIL_ENABLED=True,
            DEFAULT_FROM_EMAIL="noreply@test.local",
            EMAIL_TIMEOUT_SECONDS=5,
        ),
    )

    class FakeDestQS:
        def filter(self, **kw):
            return self
        def values_list(self, *a, **kw):
            return []

    monkeypatch.setattr(
        "apps.notifications.transports.email.EmailDestination",
        SimpleNamespace(objects=FakeDestQS()),
    )

    t = EmailNotificationTransport()
    n = _make_notification(channel="email", recipient_id="tenant-no-email")
    r = t.send(n)
    assert r.success is False
    assert r.retryable is False


# ============================================================================
# 5. Delivery service auto-resolves transport
# ============================================================================


def test_mock_fallback_for_in_app(monkeypatch):
    """in_app channel uses mock transport (fallback)."""
    called = []
    n = _make_notification(channel="in_app", status="processing")

    def fake_mark_sent(notification, provider_response=None):
        called.append((notification, provider_response))

    monkeypatch.setattr(
        "apps.notifications.services.notification_delivery_service.mark_sent",
        fake_mark_sent,
    )

    from apps.notifications.services.notification_delivery_service import deliver_notification
    deliver_notification(n)
    assert len(called) >= 1
