"""Application-level metrics abstraction.

In-memory counters that can be exported to Prometheus via django-prometheus
or a custom /metrics endpoint.

Replaces local in-memory metrics in provider_ops, notifications, etc.
"""

class _MetricsRegistry:
    """Simple in-memory registry for counters, gauges, and histograms."""

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def gauge_set(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def gauge_inc(self, name: str, value: float = 1) -> None:
        self._gauges[name] = self._gauges.get(name, 0.0) + value

    def observe(self, name: str, value: float) -> None:
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)

    def snapshot(self) -> dict:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: {"count": len(v), "sum": sum(v)} for k, v in self._histograms.items()},
        }


_registry = _MetricsRegistry()


def increment_counter(name: str, value: int = 1) -> None:
    _registry.increment(name, value)


def observe_duration(name: str, seconds: float) -> None:
    _registry.observe(name, seconds)


def set_gauge(name: str, value: float) -> None:
    _registry.gauge_set(name, value)


def get_metrics_snapshot() -> dict:
    return _registry.snapshot()
