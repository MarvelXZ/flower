from celery import shared_task

from apps.integrations.domain.enums import OutboxStatus
from apps.integrations.services.outbox_delivery_service import deliver_outbox_event
from apps.integrations.services.outbox_service import claim_pending_events


def process_integration_outbox_batch_impl(limit=100, transport=None):
    """Claim and process a batch through the replaceable provider transport."""
    events = claim_pending_events(limit=limit)
    result = {
        "claimed": len(events),
        "processed": 0,
        "retry": 0,
        "dead_letter": 0,
    }

    for event in events:
        deliver_outbox_event(event, transport)
        if event.status == OutboxStatus.PROCESSED:
            result["processed"] += 1
        elif event.status == OutboxStatus.RETRY:
            result["retry"] += 1
        elif event.status == OutboxStatus.DEAD_LETTER:
            result["dead_letter"] += 1

    return result


@shared_task(name="integrations.process_integration_outbox_batch")
def process_integration_outbox_batch(limit=100):
    return process_integration_outbox_batch_impl(limit=limit)
