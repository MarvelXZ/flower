"""SLA & escalation service for provider tasks.

Manages SLA tracking per task, detects breaches, and triggers escalations.
All mutations go through this service layer.
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.notifications.services.notification_outbox_service import enqueue_alert_notification
from apps.provider_ops.domain.enums import (
    ProviderTaskPriority,
    ProviderTaskStatus,
    TaskEscalationType,
)
from apps.provider_ops.models import (
    ProviderTask,
    TaskEscalationEvent,
    TaskSLA,
)
from apps.provider_ops.services.sla_metrics import increment_metric
from apps.provider_ops.services.sla_policy_service import (
    calculate_response_due_at,
    calculate_resolution_due_at,
)

logger = logging.getLogger(__name__)


class SLAError(ValueError):
    """Base error for SLA service failures."""


# ---------------------------------------------------------------------------
# SLA lifecycle
# ---------------------------------------------------------------------------


def create_task_sla(*, task: ProviderTask) -> TaskSLA:
    """Create SLA tracking for a task.  Idempotent — returns existing if any."""
    existing = getattr(task, "sla", None) or TaskSLA.objects.filter(task=task).first()
    if existing:
        return existing

    with transaction.atomic():
        sla = TaskSLA.objects.create(
            task=task,
            response_due_at=calculate_response_due_at(priority=task.priority),
            resolution_due_at=calculate_resolution_due_at(priority=task.priority),
        )
        return sla


def mark_task_assigned(*, task: ProviderTask) -> TaskSLA:
    """Record the first assignment time on the SLA."""
    with transaction.atomic():
        sla, _ = TaskSLA.objects.get_or_create(task=task)
        if sla.first_assigned_at is None:
            sla.first_assigned_at = timezone.now()
            sla.save(update_fields=["first_assigned_at", "updated_at"])
        return sla


def mark_task_resolved(*, task: ProviderTask) -> TaskSLA:
    """Record the resolution time on the SLA."""
    with transaction.atomic():
        sla, _ = TaskSLA.objects.get_or_create(task=task)
        sla.resolved_at = timezone.now()
        sla.save(update_fields=["resolved_at", "updated_at"])
        return sla


# ---------------------------------------------------------------------------
# Breach detection
# ---------------------------------------------------------------------------


def evaluate_task_sla(*, task: ProviderTask) -> list[TaskEscalationEvent]:
    """Evaluate a single task against its SLA targets.

    Returns a list of escalation events created during evaluation.
    """
    events: list[TaskEscalationEvent] = []

    try:
        sla = TaskSLA.objects.get(task=task)
    except TaskSLA.DoesNotExist:
        return events

    now = timezone.now()

    # Response SLA breach: task not assigned before response_due_at
    if not sla.breached_response_sla and sla.response_due_at and sla.response_due_at <= now:
        if task.status in (ProviderTaskStatus.OPEN,):
            ev = _escalate_task(task=task, escalation_type=TaskEscalationType.RESPONSE_SLA_BREACH)
            events.append(ev)
            sla.breached_response_sla = True
            sla.save(update_fields=["breached_response_sla", "updated_at"])
            increment_metric("sla_breaches_total")

    # Resolution SLA breach: task not completed before resolution_due_at
    if not sla.breached_resolution_sla and sla.resolution_due_at and sla.resolution_due_at <= now:
        if task.status not in (ProviderTaskStatus.COMPLETED, ProviderTaskStatus.CANCELLED):
            ev = _escalate_task(task=task, escalation_type=TaskEscalationType.RESOLUTION_SLA_BREACH)
            events.append(ev)
            sla.breached_resolution_sla = True
            sla.save(update_fields=["breached_resolution_sla", "updated_at"])
            increment_metric("sla_breaches_total")

            # Auto-upgrade priority if not urgent
            if task.priority != ProviderTaskPriority.URGENT:
                ev2 = _upgrade_priority(task=task)
                if ev2:
                    events.append(ev2)

    return events


def evaluate_all_open_task_slas() -> dict:
    """Evaluate SLA for all open/assigned/in_progress tasks.

    Returns a summary of breaches and escalations triggered.
    """
    result = {"evaluated": 0, "breaches": 0, "escalations": 0}
    tasks = ProviderTask.objects.filter(
        status__in={
            ProviderTaskStatus.OPEN,
            ProviderTaskStatus.ASSIGNED,
            ProviderTaskStatus.IN_PROGRESS,
        }
    )
    for task in tasks:
        events = evaluate_task_sla(task=task)
        result["evaluated"] += 1
        if events:
            result["breaches"] += 1
            result["escalations"] += len(events)
    return result


# ---------------------------------------------------------------------------
# Escalation actions
# ---------------------------------------------------------------------------


def escalate_task(*, task: ProviderTask, escalation_type: str) -> TaskEscalationEvent:
    """Create an escalation event.  Idempotent per (task, type, same level)."""
    return _escalate_task(task=task, escalation_type=escalation_type)


def _escalate_task(*, task: ProviderTask, escalation_type: str) -> TaskEscalationEvent:
    """Internal escalation — creates event and updates SLA."""
    with transaction.atomic():
        sla, _ = TaskSLA.objects.get_or_create(task=task)

        sla.escalation_level += 1
        sla.last_escalated_at = timezone.now()
        sla.save(update_fields=["escalation_level", "last_escalated_at", "updated_at"])

        event = TaskEscalationEvent.objects.create(
            task=task,
            escalation_type=escalation_type,
            metadata={"escalation_level": sla.escalation_level},
        )
        increment_metric("task_escalations_total")

        _enqueue_escalation_notification(task=task, escalation_type=escalation_type)
        return event


def upgrade_task_priority(*, task: ProviderTask) -> TaskEscalationEvent | None:
    """Upgrade a task's priority by one level.  No-op if already urgent."""
    return _upgrade_priority(task=task)


_PRIORITY_LADDER = [
    ProviderTaskPriority.LOW,
    ProviderTaskPriority.NORMAL,
    ProviderTaskPriority.HIGH,
    ProviderTaskPriority.URGENT,
]


def _upgrade_priority(*, task: ProviderTask) -> TaskEscalationEvent | None:
    """Upgrade priority one step.  Returns escalation event or None."""
    if task.priority == ProviderTaskPriority.URGENT:
        return None

    current_idx = _PRIORITY_LADDER.index(task.priority) if task.priority in _PRIORITY_LADDER else 0
    new_priority = _PRIORITY_LADDER[min(current_idx + 1, len(_PRIORITY_LADDER) - 1)]

    with transaction.atomic():
        old_priority = task.priority
        task.priority = new_priority
        task.save(update_fields=["priority", "updated_at"])

        sla, _ = TaskSLA.objects.get_or_create(task=task)
        sla.escalation_level += 1
        sla.save(update_fields=["escalation_level", "updated_at"])

        event = TaskEscalationEvent.objects.create(
            task=task,
            escalation_type=TaskEscalationType.PRIORITY_UPGRADE,
            previous_priority=old_priority,
            new_priority=new_priority,
        )

        _enqueue_escalation_notification(task=task, escalation_type=TaskEscalationType.PRIORITY_UPGRADE)
        return event


def reassign_task(*, task: ProviderTask, assignee_id: str) -> TaskEscalationEvent | None:
    """Placeholder reassignment escalation.

    Currently a no-op that creates an event for audit.  Replace with real
    reassignment logic when the provider worker pool is available.
    """
    if not assignee_id:
        return None

    with transaction.atomic():
        old_assignee = task.assignee_id
        task.assignee_id = assignee_id
        task.save(update_fields=["assignee_id", "updated_at"])

        event = TaskEscalationEvent.objects.create(
            task=task,
            escalation_type=TaskEscalationType.REASSIGNMENT,
            previous_assignee=old_assignee,
            new_assignee=assignee_id,
        )
        return event


# ---------------------------------------------------------------------------
# Notification integration
# ---------------------------------------------------------------------------


def _enqueue_escalation_notification(*, task: ProviderTask, escalation_type: str) -> None:
    """Best-effort enqueue of an escalation notification."""
    try:
        from apps.notifications.models import Alert

        title = f"Task escalated: {task.title}"
        message = f"Escalation type: {escalation_type}"

        # Create a synthetic alert to trigger notification delivery
        # This uses the existing notification outbox pipeline.
        alert = Alert.objects.create(
            alert_key=f"sla:{task.task_key}:{escalation_type}",
            source_type="system",
            title=title,
            message=message,
            rule_code=escalation_type,
            first_seen_at=timezone.now(),
            last_seen_at=timezone.now(),
        )
        enqueue_alert_notification(alert=alert, notification_type="alert_created")
    except Exception:
        logger.warning("sla_notification_enqueue_failed", extra={"task_id": task.pk, "escalation_type": escalation_type})
