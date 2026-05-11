"""Placeholder realtime notification service for provider dashboard.

Future implementation will use WebSocket or SSE to push task/SLA updates
to connected mobile/web clients.

For now this is a no-op logger placeholder.
"""

import logging

logger = logging.getLogger(__name__)


def publish_task_update(task) -> None:
    """Publish a task update event to connected clients.

    Future: push via WebSocket channel or SSE stream.
    """
    logger.debug(
        "realtime_publish_task_update",
        extra={"task_id": task.pk, "status": task.status},
    )


def publish_sla_update(task) -> None:
    """Publish an SLA update event to connected clients.

    Future: push via WebSocket channel or SSE stream.
    """
    logger.debug(
        "realtime_publish_sla_update",
        extra={"task_id": task.pk},
    )
