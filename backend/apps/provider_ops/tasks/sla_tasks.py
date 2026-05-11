"""Celery tasks for periodic SLA evaluation and escalation."""

from celery import shared_task

from apps.provider_ops.services.sla_service import evaluate_all_open_task_slas


@shared_task(name="provider_ops.evaluate_open_task_slas")
def evaluate_open_task_slas() -> dict:
    """Evaluate SLA for all open/assigned/in_progress tasks."""
    return evaluate_all_open_task_slas()


@shared_task(name="provider_ops.process_overdue_tasks")
def process_overdue_tasks() -> dict:
    """Process overdue tasks — evaluate SLA (breaches + escalations)."""
    return evaluate_all_open_task_slas()


@shared_task(name="provider_ops.send_task_reminders")
def send_task_reminders() -> dict:
    """Placeholder: send reminders for overdue tasks.

    Full implementation requires notification template support.
    Currently evaluates SLA which triggers escalation notifications.
    """
    return evaluate_all_open_task_slas()
