"""Placeholder metrics counters for SLA & escalation.

Replace with Prometheus counters when infrastructure is ready.
"""

_sla_metrics: dict[str, int | float] = {
    "sla_breaches_total": 0,
    "task_escalations_total": 0,
    "overdue_tasks_total": 0,
    "sla_response_seconds": 0,
    "sla_resolution_seconds": 0,
}


def increment_metric(name: str, value: int | float = 1) -> None:
    if name in _sla_metrics:
        _sla_metrics[name] += value
    else:
        _sla_metrics[name] = value


def observe_duration(name: str, seconds: float) -> None:
    if name in _sla_metrics and name in ("sla_response_seconds", "sla_resolution_seconds"):
        current = _sla_metrics.get(name, 0)
        count = _sla_metrics.get("sla_breaches_total", 0)
        if count > 0:
            _sla_metrics[name] = ((current * (count - 1)) + seconds) / count
        else:
            _sla_metrics[name] = seconds


def get_metrics_snapshot() -> dict:
    return dict(_sla_metrics)
