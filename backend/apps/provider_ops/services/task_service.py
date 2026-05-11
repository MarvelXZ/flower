"""Provider task lifecycle service.

All task mutations go through this service layer — never write to
``ProviderTask`` directly from views or tasks.
"""

from django.db import transaction
from django.utils import timezone

from apps.provider_ops.domain.enums import ProviderTaskEventType, ProviderTaskStatus
from apps.provider_ops.models import ProviderTask, ProviderTaskEvent, ProviderTaskNote


class TaskServiceError(ValueError):
    """Base error for task service failures."""


class InvalidTaskTransition(TaskServiceError):
    """Raised when a task status transition is not allowed."""


# ---------------------------------------------------------------------------
# Allowed status transitions
# ---------------------------------------------------------------------------

_TASK_TRANSITIONS: dict[str, set[str]] = {
    ProviderTaskStatus.OPEN: {ProviderTaskStatus.ASSIGNED, ProviderTaskStatus.IN_PROGRESS, ProviderTaskStatus.CANCELLED},
    ProviderTaskStatus.ASSIGNED: {ProviderTaskStatus.IN_PROGRESS, ProviderTaskStatus.CANCELLED},
    ProviderTaskStatus.IN_PROGRESS: {ProviderTaskStatus.COMPLETED, ProviderTaskStatus.CANCELLED},
    ProviderTaskStatus.COMPLETED: set(),  # terminal
    ProviderTaskStatus.CANCELLED: set(),  # terminal
}


def _validate_transition(current: str, target: str) -> None:
    allowed = _TASK_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTaskTransition(
            f"Cannot transition task from '{current}' to '{target}'.",
        )


def _record_event(task: ProviderTask, event_type: str, actor_id: str = "", message: str = "", metadata: dict | None = None) -> ProviderTaskEvent:
    return ProviderTaskEvent.objects.create(
        task=task,
        event_type=event_type,
        actor_id=actor_id or "",
        message=message,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_task(
    *,
    task_key: str,
    source_owner_tenant_id: str,
    task_type: str,
    title: str,
    description: str = "",
    priority: str = "",
    external_alert_id: str = "",
    external_location_id: str = "",
    external_plant_id: str = "",
    external_device_id: str = "",
    assignee_id: str = "",
    due_at=None,
    metadata: dict | None = None,
) -> ProviderTask:
    """Create a task or return existing if ``task_key`` already exists."""
    with transaction.atomic():
        existing = ProviderTask.objects.filter(task_key=task_key).first()
        if existing:
            return existing

        task = ProviderTask.objects.create(
            task_key=task_key,
            source_owner_tenant_id=source_owner_tenant_id,
            task_type=task_type,
            title=title,
            description=description,
            priority=priority or "normal",
            external_alert_id=external_alert_id or "",
            external_location_id=external_location_id or "",
            external_plant_id=external_plant_id or "",
            external_device_id=external_device_id or "",
            assignee_id=assignee_id or "",
            due_at=due_at,
            metadata=metadata or {},
        )
        _record_event(task, ProviderTaskEventType.CREATED, message="Task created.")
        return task


def assign_task(*, task: ProviderTask, assignee_id: str) -> ProviderTask:
    """Assign a task to a provider worker."""
    with transaction.atomic():
        _validate_transition(task.status, ProviderTaskStatus.ASSIGNED)
        task.status = ProviderTaskStatus.ASSIGNED
        task.assignee_id = assignee_id
        task.save(update_fields=["status", "assignee_id", "updated_at"])
        _record_event(task, ProviderTaskEventType.ASSIGNED, actor_id=assignee_id, message=f"Assigned to {assignee_id}.")
        return task


def start_task(*, task: ProviderTask) -> ProviderTask:
    """Mark a task as in progress."""
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(task.status, ProviderTaskStatus.IN_PROGRESS)
        task.status = ProviderTaskStatus.IN_PROGRESS
        task.started_at = now
        task.save(update_fields=["status", "started_at", "updated_at"])
        _record_event(task, ProviderTaskEventType.STARTED, message="Task started.")
        return task


def complete_task(*, task: ProviderTask, completion_note: str = "") -> ProviderTask:
    """Mark a task as completed (terminal)."""
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(task.status, ProviderTaskStatus.COMPLETED)
        task.status = ProviderTaskStatus.COMPLETED
        task.completed_at = now
        task.save(update_fields=["status", "completed_at", "updated_at"])
        _record_event(task, ProviderTaskEventType.COMPLETED, message=completion_note or "Task completed.")
        if completion_note:
            ProviderTaskNote.objects.create(task=task, body=completion_note)
        return task


def cancel_task(*, task: ProviderTask, reason: str = "") -> ProviderTask:
    """Cancel a task (terminal)."""
    now = timezone.now()
    with transaction.atomic():
        _validate_transition(task.status, ProviderTaskStatus.CANCELLED)
        task.status = ProviderTaskStatus.CANCELLED
        task.cancelled_at = now
        task.save(update_fields=["status", "cancelled_at", "updated_at"])
        _record_event(task, ProviderTaskEventType.CANCELLED, message=reason or "Task cancelled.")
        return task


def add_task_note(*, task: ProviderTask, body: str, actor_id: str = "") -> ProviderTaskNote:
    """Add a free-text note to a task."""
    with transaction.atomic():
        note = ProviderTaskNote.objects.create(task=task, actor_id=actor_id or "", body=body)
        _record_event(task, ProviderTaskEventType.NOTE_ADDED, actor_id=actor_id, message="Note added.")
        return note
