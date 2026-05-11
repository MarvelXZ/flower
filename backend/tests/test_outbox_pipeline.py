"""Phase 3 tests for IntegrationOutbox pipeline hardening."""

from contextlib import nullcontext
from dataclasses import dataclass
from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from apps.integrations.domain.constants import MAX_RETRY_COUNT
from apps.integrations.domain.enums import OutboxStatus
from apps.integrations.selectors.outbox_selectors import (
    get_pending_outbox_events,
    is_claimable_outbox_event,
)
from apps.integrations.services import outbox_service
from apps.integrations.tasks import outbox_tasks


@dataclass
class FakeOutboxEvent:
    status: str
    available_at: object
    created_at: object | None = None
    retry_count: int = 0
    attempts: int = 0
    last_error: str = ""
    processed_at: object | None = None
    saved_update_fields: list[str] | None = None

    def save(self, *, update_fields):
        self.saved_update_fields = list(update_fields)


def test_pending_selector_uses_skip_locked_claim_pattern():
    queryset = get_pending_outbox_events(limit=25)

    assert queryset.query.select_for_update is True
    assert queryset.query.select_for_update_skip_locked is True
    assert queryset.query.order_by == ("available_at", "created_at")
    assert queryset.query.high_mark == 25


def test_pending_event_can_be_claimed(monkeypatch):
    event = FakeOutboxEvent(status=OutboxStatus.PENDING, available_at=timezone.now())

    monkeypatch.setattr(outbox_service.transaction, "atomic", lambda: nullcontext())
    monkeypatch.setattr(outbox_service, "get_pending_outbox_events", lambda limit: [event])

    claimed = outbox_service.claim_pending_events(limit=1)

    assert claimed == [event]
    assert event.status == OutboxStatus.PROCESSING
    assert event.saved_update_fields == ["status", "updated_at"]


def test_retry_event_with_past_available_at_can_be_claimed():
    now = timezone.now()
    event = FakeOutboxEvent(
        status=OutboxStatus.RETRY,
        available_at=now - timedelta(seconds=1),
    )

    assert is_claimable_outbox_event(event, now=now) is True


def test_retry_event_with_future_available_at_cannot_be_claimed():
    now = timezone.now()
    event = FakeOutboxEvent(
        status=OutboxStatus.RETRY,
        available_at=now + timedelta(seconds=60),
    )

    assert is_claimable_outbox_event(event, now=now) is False


def test_processing_can_be_marked_processed():
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSING, available_at=timezone.now())

    outbox_service.mark_processed(event)

    assert event.status == OutboxStatus.PROCESSED
    assert event.processed_at is not None
    assert event.last_error == ""


def test_processing_can_be_marked_retry():
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSING, available_at=timezone.now())

    outbox_service.mark_retry(event, error="temporary failure", retry_delay_seconds=30)

    assert event.status == OutboxStatus.RETRY
    assert event.retry_count == 1
    assert event.last_error == "temporary failure"
    assert event.available_at > timezone.now()


def test_processing_can_be_marked_dead_letter():
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSING, available_at=timezone.now())

    outbox_service.mark_dead_letter(event, error="permanent failure")

    assert event.status == OutboxStatus.DEAD_LETTER
    assert event.retry_count == 1
    assert event.last_error == "permanent failure"


def test_pending_cannot_be_marked_processed_directly():
    event = FakeOutboxEvent(status=OutboxStatus.PENDING, available_at=timezone.now())

    with pytest.raises(outbox_service.InvalidOutboxTransition):
        outbox_service.mark_processed(event)


def test_processed_cannot_move_back_to_retry():
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSED, available_at=timezone.now())

    with pytest.raises(outbox_service.InvalidOutboxTransition):
        outbox_service.mark_retry(event, error="nope", retry_delay_seconds=30)


def test_delivery_attempt_is_recorded(monkeypatch):
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSING, available_at=timezone.now())
    created = {}

    class FakeDeliveryManager:
        def create(self, **kwargs):
            created.update(kwargs)
            return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        outbox_service,
        "OutboxDelivery",
        SimpleNamespace(objects=FakeDeliveryManager()),
    )

    delivery = outbox_service.record_delivery_attempt(
        event,
        OutboxStatus.RETRY,
        error="timeout",
    )

    assert event.attempts == 1
    assert delivery.attempt_number == 1
    assert created["outbox"] is event
    assert created["status"] == OutboxStatus.RETRY
    assert created["error"] == "timeout"


def test_celery_task_processes_batch_with_placeholder(monkeypatch):
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSING, available_at=timezone.now())

    monkeypatch.setattr(outbox_tasks, "claim_pending_events", lambda limit: [event])
    monkeypatch.setattr(
        outbox_tasks,
        "deliver_outbox_event",
        lambda event, transport: setattr(event, "status", OutboxStatus.PROCESSED),
    )

    result = outbox_tasks.process_integration_outbox_batch_impl(limit=10)

    assert result == {"claimed": 1, "processed": 1, "retry": 0, "dead_letter": 0}
    assert event.status == OutboxStatus.PROCESSED


def test_celery_task_marks_retry_on_placeholder_failure(monkeypatch):
    event = FakeOutboxEvent(status=OutboxStatus.PROCESSING, available_at=timezone.now())

    monkeypatch.setattr(outbox_tasks, "claim_pending_events", lambda limit: [event])
    monkeypatch.setattr(
        outbox_tasks,
        "deliver_outbox_event",
        lambda event, transport: setattr(event, "status", OutboxStatus.RETRY),
    )

    result = outbox_tasks.process_integration_outbox_batch_impl(limit=10)

    assert result == {"claimed": 1, "processed": 0, "retry": 1, "dead_letter": 0}
    assert event.status == OutboxStatus.RETRY


def test_celery_task_marks_dead_letter_after_max_retries(monkeypatch):
    event = FakeOutboxEvent(
        status=OutboxStatus.PROCESSING,
        available_at=timezone.now(),
        retry_count=MAX_RETRY_COUNT - 1,
    )

    monkeypatch.setattr(outbox_tasks, "claim_pending_events", lambda limit: [event])
    monkeypatch.setattr(
        outbox_tasks,
        "deliver_outbox_event",
        lambda event, transport: setattr(event, "status", OutboxStatus.DEAD_LETTER),
    )

    result = outbox_tasks.process_integration_outbox_batch_impl(limit=10)

    assert result == {"claimed": 1, "processed": 0, "retry": 0, "dead_letter": 1}
    assert event.status == OutboxStatus.DEAD_LETTER
