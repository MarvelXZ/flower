def is_owner_capable(kind: str) -> bool:
    return kind in {"owner", "hybrid"}


def is_provider_capable(kind: str) -> bool:
    return kind in {"provider", "hybrid"}
