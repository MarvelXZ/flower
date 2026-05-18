"""Core HTML views for shared PlantOps interface surfaces."""

from datetime import datetime, timezone

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone as django_timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django_tenants.utils import tenant_context

from apps.core.metrics import get_metrics_snapshot
from apps.core.services.runtime_health_service import get_dependency_health, get_runtime_health
from apps.devices.models import Device
from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client


class UIKitView(TemplateView):
    """Render the shared Django and HTMX UI kit."""

    template_name = "ui_kit/index.html"


class PlatformHomeView(TemplateView):
    """Render the public platform presentation page."""

    template_name = "marketing/platform_home.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    """Render the default operations dashboard."""

    login_url = "/admin/login/"
    template_name = "dashboard/index.html"
    max_missed_heartbeats = 3

    def get_active_owner_tenants(self):
        return Client.objects.filter(
            is_active=True,
            kind__in=[TenantKind.OWNER, TenantKind.HYBRID],
        ).order_by("name")

    def get_device_health(self, device, now):
        if device.status == "retired":
            return "muted", "Retired"
        if device.status == "offline":
            return "danger", "Offline"
        if not device.last_seen_at:
            return "muted", "Never seen"

        stale_after_seconds = device.heartbeat_interval_seconds * self.max_missed_heartbeats
        age_seconds = (now - device.last_seen_at).total_seconds()
        if age_seconds <= stale_after_seconds:
            return "ok", "Online"
        return "warning", "Stale"

    def get_platform_device_summary(self):
        now = django_timezone.now()
        rows = []

        for tenant in self.get_active_owner_tenants():
            with tenant_context(tenant):
                for device in Device.objects.order_by("-last_seen_at", "name")[:50]:
                    health_status, health_label = self.get_device_health(device, now)
                    rows.append(
                        {
                            "tenant_name": tenant.name,
                            "tenant_schema": tenant.schema_name,
                            "name": device.name,
                            "serial_number": device.serial_number,
                            "status": device.get_status_display(),
                            "health_status": health_status,
                            "health_label": health_label,
                            "last_seen_at": device.last_seen_at,
                        }
                    )

        rows.sort(key=lambda item: item["last_seen_at"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return rows

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        devices = self.get_platform_device_summary()
        dependency_health = get_dependency_health()
        unhealthy_dependencies = [
            name for name, data in dependency_health.items()
            if data.get("status") != "healthy"
        ]

        context.update(
            {
                "sidebar_active": "dashboard",
                "tenant_count": Client.objects.count(),
                "active_tenant_count": Client.objects.filter(is_active=True).count(),
                "kpi_active_devices": sum(1 for device in devices if device["health_status"] == "ok"),
                "kpi_total_devices": len(devices),
                "kpi_attention_devices": sum(
                    1 for device in devices if device["health_status"] in {"warning", "danger"}
                ),
                "kpi_never_seen_devices": sum(
                    1 for device in devices if device["health_label"] == "Never seen"
                ),
                "recent_devices": devices[:10],
                "dependency_health": dependency_health,
                "unhealthy_dependencies": unhealthy_dependencies,
            }
        )
        return context


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
