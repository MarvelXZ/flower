"""Read-only queries for provider tasks."""

from django.utils import timezone

from apps.provider_ops.domain.enums import ProviderTaskStatus
from apps.provider_ops.models import ProviderTask


def list_open_tasks():
    """Return all non-terminal tasks."""
    return ProviderTask.objects.filter(
        status__in={
            ProviderTaskStatus.OPEN,
            ProviderTaskStatus.ASSIGNED,
            ProviderTaskStatus.IN_PROGRESS,
        },
    ).order_by("-priority", "created_at")


def list_tasks_for_assignee(*, assignee_id: str):
    """Return tasks assigned to a specific provider worker."""
    return ProviderTask.objects.filter(
        assignee_id=assignee_id,
        status__in={
            ProviderTaskStatus.ASSIGNED,
            ProviderTaskStatus.IN_PROGRESS,
        },
    ).order_by("-priority", "created_at")


def get_task_by_key(*, task_key: str) -> ProviderTask | None:
    """Look up a task by its idempotency key."""
    try:
        return ProviderTask.objects.get(task_key=task_key)
    except ProviderTask.DoesNotExist:
        return None


def list_overdue_tasks(*, now=None):
    """Return open/assigned/in_progress tasks that are past due."""
    current_time = now or timezone.now()
    return ProviderTask.objects.filter(
        status__in={
            ProviderTaskStatus.OPEN,
            ProviderTaskStatus.ASSIGNED,
            ProviderTaskStatus.IN_PROGRESS,
        },
        due_at__isnull=False,
        due_at__lt=current_time,
    ).order_by("due_at")


def task_dashboard_summary():
    """Return aggregate counts for a provider task dashboard."""
    now = timezone.now()
    total = ProviderTask.objects.count()
    return {
        "total": total,
        "open": ProviderTask.objects.filter(status=ProviderTaskStatus.OPEN).count(),
        "assigned": ProviderTask.objects.filter(status=ProviderTaskStatus.ASSIGNED).count(),
        "in_progress": ProviderTask.objects.filter(status=ProviderTaskStatus.IN_PROGRESS).count(),
        "completed": ProviderTask.objects.filter(status=ProviderTaskStatus.COMPLETED).count(),
        "cancelled": ProviderTask.objects.filter(status=ProviderTaskStatus.CANCELLED).count(),
        "overdue": ProviderTask.objects.filter(
            status__in={
                ProviderTaskStatus.OPEN,
                ProviderTaskStatus.ASSIGNED,
                ProviderTaskStatus.IN_PROGRESS,
            },
            due_at__isnull=False,
            due_at__lt=now,
        ).count(),
    }
