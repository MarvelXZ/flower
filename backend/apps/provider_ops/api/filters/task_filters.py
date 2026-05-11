"""Filter definitions for provider task queries.

Supports query-param based filtering:
- status
- priority
- task_type
- assignee_id
- overdue (bool)
- breached (bool)
- created_after / created_before
"""

from django.db.models import Q
from django.utils import timezone


class TaskFilter:
    """Lightweight filter helper — no django-filter dependency required.

    Apply with: ``TaskFilter(request.GET).apply(queryset)``.
    """

    def __init__(self, query_params: dict):
        self.params = query_params

    def apply(self, qs):
        data = self.params

        if status_val := data.get("status"):
            qs = qs.filter(status=status_val)

        if priority_val := data.get("priority"):
            qs = qs.filter(priority=priority_val)

        if task_type_val := data.get("task_type"):
            qs = qs.filter(task_type=task_type_val)

        if assignee := data.get("assignee_id"):
            qs = qs.filter(assignee_id=assignee)

        if data.get("overdue") in ("true", "1"):
            now = timezone.now()
            qs = qs.filter(
                status__in={"open", "assigned", "in_progress"},
                sla__resolution_due_at__isnull=False,
                sla__resolution_due_at__lt=now,
            )

        if data.get("breached") in ("true", "1"):
            qs = qs.filter(
                Q(sla__breached_response_sla=True) | Q(sla__breached_resolution_sla=True),
            )

        if after := data.get("created_after"):
            qs = qs.filter(created_at__gte=after)

        if before := data.get("created_before"):
            qs = qs.filter(created_at__lte=before)

        return qs
