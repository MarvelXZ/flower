"""SLA policy definitions for provider task resolution and response times.

Default SLA targets per priority level.  Future phases will allow per-tenant
or per-provider overrides.
"""

import datetime

from django.utils import timezone

from apps.provider_ops.domain.enums import ProviderTaskPriority


# SLA targets in hours: (response_hours, resolution_hours)
_SLA_POLICIES: dict[str, tuple[float, float]] = {
    ProviderTaskPriority.LOW: (24.0, 72.0),
    ProviderTaskPriority.NORMAL: (8.0, 24.0),
    ProviderTaskPriority.HIGH: (2.0, 8.0),
    ProviderTaskPriority.URGENT: (0.25, 2.0),  # 15 min / 2 h
}


def get_priority_sla(priority: str) -> tuple[float, float]:
    """Return ``(response_hours, resolution_hours)`` for a priority."""
    return _SLA_POLICIES.get(priority, _SLA_POLICIES[ProviderTaskPriority.NORMAL])


def calculate_response_due_at(*, priority: str) -> datetime.datetime:
    """Calculate ``response_due_at`` based on priority."""
    hours, _ = get_priority_sla(priority)
    return timezone.now() + datetime.timedelta(hours=hours)


def calculate_resolution_due_at(*, priority: str) -> datetime.datetime:
    """Calculate ``resolution_due_at`` based on priority."""
    _, hours = get_priority_sla(priority)
    return timezone.now() + datetime.timedelta(hours=hours)


def get_task_sla_policy(*, priority: str) -> dict:
    """Return the full SLA policy for a given priority."""
    response_h, resolution_h = get_priority_sla(priority)
    return {
        "priority": priority,
        "response_hours": response_h,
        "resolution_hours": resolution_h,
        "response_due_at": calculate_response_due_at(priority=priority),
        "resolution_due_at": calculate_resolution_due_at(priority=priority),
    }
