from apps.integrations.domain.enums import OutboxStatus


def can_claim(status: str) -> bool:
    return status in {OutboxStatus.PENDING, OutboxStatus.RETRY}


def can_retry(status: str) -> bool:
    return status == OutboxStatus.PROCESSING
