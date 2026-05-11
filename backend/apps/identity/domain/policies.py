def can_access_provider_ops(role: str) -> bool:
    return role in {"admin", "provider_operator"}
