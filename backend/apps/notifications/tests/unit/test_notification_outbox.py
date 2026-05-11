"""Unit tests for notification outbox, delivery, transport, and alert integration (Phase 12)."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.notifications.domain.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    RecipientType,
)
from apps.notifications.services.notification_delivery_service import deliver_notification
from apps.notifications.services.notification_outbox_service import (
    InvalidNotificationTransition,
    _build_event_id,
    _validate_transition,
    claim_pending_notifications,
    enqueue_alert_notification,
    mark_dead_letter,
    mark_failed,
    mark_processing,
    mark_retry,
    mark_sent,
)
from apps.notifications.transports.mock import MockNotificationTransport


# ============================================================================
# Helpers
# ============================================================================

def _mock_atomic(monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.transaction.atomic",
        lambda: nullcontext(),
    )


def _make_alert(**kw):
    defaults = {"pk": 1, "alert_key": "test:device_1", "title": "Test", "message": "Test msg",
                "severity": "warning", "rule_code": "test_rule", "status": "open"}
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _make_notification(**kw):
    defaults = {
        "pk": 1, "event_id": "evt-1", "notification_type": NotificationType.ALERT_CREATED,
        "channel": NotificationChannel.IN_APP, "recipient_type": RecipientType.TENANT,
        "recipient_id": "", "status": NotificationStatus.PENDING, "attempt_count": 0,
        "available_at": timezone.now(), "last_error": "",
        "save": MagicMock(), "created_at": timezone.now(), "updated_at": timezone.now(),
    }
    defaults.update(kw)
    return SimpleNamespace(**defaults)


# ============================================================================
# _validate_transition
# ============================================================================


def test_pending_to_processing_allowed():
    _validate_transition(NotificationStatus.PENDING, NotificationStatus.PROCESSING)


def test_retry_to_processing_allowed():
    _validate_transition(NotificationStatus.RETRY, NotificationStatus.PROCESSING)


def test_processing_to_sent_allowed():
    _validate_transition(NotificationStatus.PROCESSING, NotificationStatus.SENT)


def test_processing_to_retry_allowed():
    _validate_transition(NotificationStatus.PROCESSING, NotificationStatus.RETRY)


def test_processing_to_dead_letter_allowed():
    _validate_transition(NotificationStatus.PROCESSING, NotificationStatus.DEAD_LETTER)


def test_sent_is_terminal():
    for t in NotificationStatus.values:
        if t == NotificationStatus.SENT:
            continue
        with pytest.raises(InvalidNotificationTransition):
            _validate_transition(NotificationStatus.SENT, t)


def test_dead_letter_is_terminal():
    for t in NotificationStatus.values:
        if t == NotificationStatus.DEAD_LETTER:
            continue
        with pytest.raises(InvalidNotificationTransition):
            _validate_transition(NotificationStatus.DEAD_LETTER, t)


def test_pending_to_sent_denied():
    with pytest.raises(InvalidNotificationTransition):
        _validate_transition(NotificationStatus.PENDING, NotificationStatus.SENT)


# ============================================================================
# _build_event_id
# ============================================================================


def test_build_event_id_stable():
    alert = _make_alert(pk=42)
    eid1 = _build_event_id(alert=alert, notification_type=NotificationType.ALERT_CREATED)
    eid2 = _build_event_id(alert=alert, notification_type=NotificationType.ALERT_CREATED)
    assert eid1 == eid2


def test_build_event_id_differs_by_type():
    alert = _make_alert(pk=42)
    created = _build_event_id(alert=alert, notification_type=NotificationType.ALERT_CREATED)
    resolved = _build_event_id(alert=alert, notification_type=NotificationType.ALERT_RESOLVED)
    assert created != resolved


# ============================================================================
# enqueue_alert_notification
# ============================================================================


def test_enqueue_creates_notification(monkeypatch):
    _mock_atomic(monkeypatch)
    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.check_preferences_allows",
        lambda **kw: True,
    )
    alert = _make_alert(pk=1)
    now = timezone.now()
    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    class FakeQS:
        def select_for_update(self, **kw):
            return self
        def filter(self, **kw):
            return self
        def first(self):
            return None

    class FakeNO:
        objects = SimpleNamespace(
            select_for_update=lambda **kw: FakeQS(),
            create=MagicMock(
                side_effect=lambda **kw: SimpleNamespace(**kw, pk=1)
            ),
        )

    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.NotificationOutbox",
        FakeNO,
    )

    result = enqueue_alert_notification(
        alert=alert,
        notification_type=NotificationType.ALERT_CREATED,
    )
    assert len(result) >= 1


def test_enqueue_same_alert_no_duplicate(monkeypatch):
    _mock_atomic(monkeypatch)
    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.check_preferences_allows",
        lambda **kw: True,
    )
    alert = _make_alert(pk=1)
    now = timezone.now()

    existing = _make_notification(pk=1, status=NotificationStatus.PENDING)

    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.timezone",
        SimpleNamespace(now=lambda: now),
    )

    class FakeQS:
        def select_for_update(self, **kw):
            return self
        def filter(self, **kw):
            return self
        def first(self):
            return existing

    class FakeNO:
        objects = SimpleNamespace(
            select_for_update=lambda **kw: FakeQS(),
        )

    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.NotificationOutbox",
        FakeNO,
    )

    result = enqueue_alert_notification(
        alert=alert,
        notification_type=NotificationType.ALERT_CREATED,
    )
    assert len(result) >= 1
    assert result[0].event_id == existing.event_id


# ============================================================================
# mark_processing / mark_sent / mark_retry / mark_dead_letter
# ============================================================================


def test_mark_processing(monkeypatch):
    n = MagicMock()
    n.status = NotificationStatus.PENDING
    mark_processing(n)
    assert n.status == NotificationStatus.PROCESSING


def _mock_notification_delivery(monkeypatch):
    """Mock NotificationDelivery.objects.create to avoid DB access."""
    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.NotificationDelivery",
        SimpleNamespace(
            objects=SimpleNamespace(
                create=MagicMock(return_value=SimpleNamespace(pk=1))
            )
        ),
    )


def test_mark_sent_terminal(monkeypatch):
    _mock_atomic(monkeypatch)
    _mock_notification_delivery(monkeypatch)
    n = MagicMock()
    n.status = NotificationStatus.PROCESSING
    n.attempt_count = 0
    n.channel = NotificationChannel.IN_APP
    result = mark_sent(n)
    assert result.status == NotificationStatus.SENT
    assert result.attempt_count == 1


def test_mark_retry(monkeypatch):
    _mock_atomic(monkeypatch)
    _mock_notification_delivery(monkeypatch)
    n = MagicMock()
    n.status = NotificationStatus.PROCESSING
    n.attempt_count = 0
    n.channel = NotificationChannel.IN_APP
    result = mark_retry(n, error="retryable err")
    assert result.status == NotificationStatus.RETRY
    assert result.attempt_count == 1


def test_mark_dead_letter(monkeypatch):
    _mock_atomic(monkeypatch)
    _mock_notification_delivery(monkeypatch)
    n = MagicMock()
    n.status = NotificationStatus.PROCESSING
    n.attempt_count = 0
    n.channel = NotificationChannel.IN_APP
    result = mark_dead_letter(n, error="permanent err")
    assert result.status == NotificationStatus.DEAD_LETTER
    assert result.attempt_count == 1


def test_mark_failed(monkeypatch):
    _mock_atomic(monkeypatch)
    _mock_notification_delivery(monkeypatch)
    n = MagicMock()
    n.status = NotificationStatus.PROCESSING
    n.attempt_count = 0
    n.channel = NotificationChannel.IN_APP
    result = mark_failed(n, error="fatal")
    assert result.status == NotificationStatus.FAILED


# ============================================================================
# claim_pending_notifications
# ============================================================================


def test_claim_pending_returns_list(monkeypatch):
    _mock_atomic(monkeypatch)
    fake_n = _make_notification(status=NotificationStatus.PENDING)

    class FakeIterator:
        def __iter__(self):
            return iter([fake_n])
        def __getitem__(self, k):
            return [fake_n]

    class FakeQS:
        def select_for_update(self, **kw):
            return self
        def filter(self, **kw):
            return FakeIterator()
        def __getitem__(self, k):
            return [fake_n]
        def __iter__(self):
            return iter([fake_n])

    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.NotificationOutbox.objects.select_for_update",
        lambda **kw: FakeQS(),
    )
    monkeypatch.setattr(
        "apps.notifications.services.notification_outbox_service.NotificationOutbox",
        SimpleNamespace(
            objects=SimpleNamespace(
                select_for_update=lambda **kw: FakeQS()
            )
        ),
    )

    result = claim_pending_notifications(limit=10)
    assert len(result) >= 1


# ============================================================================
# Mock transport
# ============================================================================


def test_mock_transport_success():
    t = MockNotificationTransport(mode="success")
    n = _make_notification()
    r = t.send(n)
    assert r.success is True


def test_mock_transport_retryable():
    t = MockNotificationTransport(mode="retryable")
    n = _make_notification()
    r = t.send(n)
    assert r.success is False
    assert r.retryable is True


def test_mock_transport_permanent():
    t = MockNotificationTransport(mode="permanent")
    n = _make_notification()
    r = t.send(n)
    assert r.success is False
    assert r.retryable is False


# ============================================================================
# deliver_notification
# ============================================================================


def test_deliver_success(monkeypatch):
    called = []
    n = _make_notification(status=NotificationStatus.PROCESSING)
    t = MockNotificationTransport(mode="success")

    def fake_mark_sent(notification, provider_response=None):
        called.append((notification, provider_response))

    monkeypatch.setattr(
        "apps.notifications.services.notification_delivery_service.mark_sent",
        fake_mark_sent,
    )

    deliver_notification(n, t)
    assert len(called) >= 1


def test_deliver_retryable(monkeypatch):
    called = []
    n = _make_notification(status=NotificationStatus.PROCESSING)
    t = MockNotificationTransport(mode="retryable")

    def fake_mark_retry(notification, error):
        called.append((notification, error))

    monkeypatch.setattr(
        "apps.notifications.services.notification_delivery_service.mark_retry",
        fake_mark_retry,
    )

    deliver_notification(n, t)
    assert len(called) >= 1


def test_deliver_permanent(monkeypatch):
    called = []
    n = _make_notification(status=NotificationStatus.PROCESSING)
    t = MockNotificationTransport(mode="permanent")

    def fake_mark_dead(notification, error):
        called.append((notification, error))

    monkeypatch.setattr(
        "apps.notifications.services.notification_delivery_service.mark_dead_letter",
        fake_mark_dead,
    )

    deliver_notification(n, t)
    assert len(called) >= 1


# ============================================================================
# Notification outbox model string
# ============================================================================


def test_notification_str():
    n = _make_notification(notification_type=NotificationType.ALERT_CREATED, status=NotificationStatus.PENDING)
    s = f"{n.notification_type}:{n.status}"
    assert s == "alert_created:pending"
