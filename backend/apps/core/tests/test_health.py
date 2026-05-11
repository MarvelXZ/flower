"""Unit tests for healthcheck endpoints and runtime health service (Phase 17)."""



from django.http import HttpRequest

from apps.core.services.runtime_health_service import (
    get_dependency_health,
    get_runtime_health,
)
from apps.core.views import core_health_live, core_health_ready


# ============================================================================
# 1. Health check views
# ============================================================================


def test_health_live_returns_alive():
    request = HttpRequest()
    response = core_health_live(request)
    assert response.status_code == 200
    import json
    data = json.loads(response.content)
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_health_ready_returns_status(monkeypatch):
    request = HttpRequest()
    monkeypatch.setattr(
        "apps.core.views.get_dependency_health",
        lambda: {"database": {"status": "healthy", "detail": "OK"},
                "redis": {"status": "healthy", "detail": "OK"},
                "celery": {"status": "healthy", "detail": "OK"}},
    )
    response = core_health_ready(request)
    assert response.status_code == 200
    import json
    data = json.loads(response.content)
    assert "status" in data
    assert "checks" in data


# ============================================================================
# 2. Runtime health service
# ============================================================================


def test_get_dependency_health_returns_dict(monkeypatch):
    monkeypatch.setattr(
        "apps.core.services.runtime_health_service._check_database",
        lambda: {"status": "healthy"},
    )
    monkeypatch.setattr(
        "apps.core.services.runtime_health_service._check_redis",
        lambda: {"status": "healthy"},
    )
    monkeypatch.setattr(
        "apps.core.services.runtime_health_service._check_celery",
        lambda: {"status": "healthy"},
    )
    deps = get_dependency_health()
    assert "database" in deps
    assert "redis" in deps
    assert "celery" in deps


def test_get_runtime_health_aggregate(monkeypatch):
    monkeypatch.setattr(
        "apps.core.services.runtime_health_service.get_dependency_health",
        lambda: {"database": {"status": "healthy"}},
    )
    health = get_runtime_health()
    assert health["status"] == "healthy"
    assert "checks" in health
    assert "timestamp" in health


def test_get_runtime_health_degraded(monkeypatch):
    monkeypatch.setattr(
        "apps.core.services.runtime_health_service.get_dependency_health",
        lambda: {
            "database": {"status": "healthy"},
            "redis": {"status": "degraded", "detail": "down"},
        },
    )
    health = get_runtime_health()
    assert health["status"] == "degraded"


# ============================================================================
# 3. Metrics abstraction
# ============================================================================


def test_metrics_increment_counter():
    from apps.core.metrics import increment_counter, get_metrics_snapshot
    increment_counter("test_requests", 5)
    snap = get_metrics_snapshot()
    assert snap["counters"].get("test_requests") == 5


def test_metrics_observe_duration():
    from apps.core.metrics import get_metrics_snapshot, observe_duration
    observe_duration("request_latency", 0.5)
    snap = get_metrics_snapshot()
    assert snap["histograms"]["request_latency"]["count"] >= 1


def test_metrics_set_gauge():
    from apps.core.metrics import get_metrics_snapshot, set_gauge
    set_gauge("active_connections", 10)
    snap = get_metrics_snapshot()
    assert snap["gauges"]["active_connections"] == 10
