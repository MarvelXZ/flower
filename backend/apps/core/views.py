"""Core HTML views for shared PlantOps interface surfaces."""

from datetime import datetime, timezone

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.core.metrics import get_metrics_snapshot
from apps.core.services.runtime_health_service import get_dependency_health, get_runtime_health


class UIKitView(TemplateView):
    """Render the shared Django and HTMX UI kit."""

    template_name = "ui_kit/index.html"


class DashboardView(TemplateView):
    """Render the default operations dashboard."""

    template_name = "dashboard/index.html"


def core_health_live(request):
    """Liveness probe — returns immediately if process is alive."""
    return JsonResponse({"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()})


def core_health_ready(request):
    """Readiness probe — checks DB and Redis connectivity."""
    deps = get_dependency_health()
    overall = "ready"
    for dep in deps.values():
        if dep.get("status") != "healthy":
            overall = "degraded"
            break
    return JsonResponse({
        "status": overall,
        "checks": deps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def core_health_summary(request):
    """Aggregate health summary."""
    data = get_runtime_health()
    return JsonResponse(data)


def core_metrics_endpoint(request):
    """Prometheus-compatible metrics export endpoint.

    Exports in-memory counters, gauges, and histograms in the
    Prometheus text exposition format."""
    snapshot = get_metrics_snapshot()
    lines = []

    for name, value in snapshot["counters"].items():
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")

    for name, value in snapshot["gauges"].items():
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value:.6f}")

    for name, stats in snapshot["histograms"].items():
        lines.append(f"# TYPE {name} summary")
        lines.append(f"{name}_count {stats['count']}")
        lines.append(f"{name}_sum {stats['sum']:.6f}")

    lines.append(f"# EOF")
    return JsonResponse(
        "\n".join(lines) + "\n",
        safe=False,
        content_type="text/plain; version=0.0.4",
    )


@require_POST
def ui_kit_sample(request):
    """Return a small HTMX fragment used by the UI kit demo form."""

    return render(request, "partials/ui_feedback.html")
