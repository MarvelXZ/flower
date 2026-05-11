"""Core HTML views for shared PlantOps interface surfaces."""

from datetime import datetime, timezone

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

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


@require_POST
def ui_kit_sample(request):
    """Return a small HTMX fragment used by the UI kit demo form."""

    return render(request, "partials/ui_feedback.html")
