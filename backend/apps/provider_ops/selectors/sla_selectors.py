"""Read-only queries for SLA and escalation data."""

from django.db.models import Avg, Q
from django.utils import timezone

from apps.provider_ops.domain.enums import ProviderTaskPriority, ProviderTaskStatus
from apps.provider_ops.models import ProviderTask, TaskEscalationEvent, TaskSLA


def list_overdue_tasks(*, now=None):
    """Return non-terminal tasks past their resolution due date."""
    current_time = now or timezone.now()
    return ProviderTask.objects.filter(
        status__in={
            ProviderTaskStatus.OPEN,
            ProviderTaskStatus.ASSIGNED,
            ProviderTaskStatus.IN_PROGRESS,
        },
        sla__resolution_due_at__isnull=False,
        sla__resolution_due_at__lt=current_time,
    ).select_related("sla").order_by("sla__resolution_due_at")


def list_breached_tasks():
    """Return tasks with breached SLA flags."""
    return ProviderTask.objects.filter(
        Q(sla__breached_response_sla=True) | Q(sla__breached_resolution_sla=True),
    ).select_related("sla").order_by("-sla__updated_at")


def list_urgent_unassigned_tasks():
    """Return urgent tasks that are not yet assigned."""
    return ProviderTask.objects.filter(
        priority=ProviderTaskPriority.URGENT,
        status=ProviderTaskStatus.OPEN,
    ).order_by("created_at")


def sla_dashboard_summary():
    """Return aggregate SLA dashboard metrics."""
    now = timezone.now()
    tasks = ProviderTask.objects.filter(
        status__in={
            ProviderTaskStatus.OPEN,
            ProviderTaskStatus.ASSIGNED,
            ProviderTaskStatus.IN_PROGRESS,
        },
    )
    return {
        "overdue_count": tasks.filter(
            sla__resolution_due_at__isnull=False,
            sla__resolution_due_at__lt=now,
        ).count(),
        "breached_count": ProviderTask.objects.filter(
            Q(sla__breached_response_sla=True) | Q(sla__breached_resolution_sla=True),
        ).count(),
        "urgent_open_count": ProviderTask.objects.filter(
            priority=ProviderTaskPriority.URGENT,
            status=ProviderTaskStatus.OPEN,
        ).count(),
        "escalation_count": TaskEscalationEvent.objects.count(),
        "avg_response_time": TaskSLA.objects.filter(
            first_assigned_at__isnull=False,
        ).aggregate(
            avg=Avg(
                timezone.now() - timezone.now()  # placeholder
            )
        )["avg"],
    }
