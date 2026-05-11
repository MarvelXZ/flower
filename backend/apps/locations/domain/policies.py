def can_assign_plants(kind: str) -> bool:
    return kind in {"site", "building", "room", "area"}
