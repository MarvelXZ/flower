def requires_push(severity: str) -> bool:
    return severity in {"warning", "critical"}
