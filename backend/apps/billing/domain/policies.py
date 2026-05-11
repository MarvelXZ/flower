def is_billable(status: str) -> bool:
    return status in {"trial", "active", "past_due"}
