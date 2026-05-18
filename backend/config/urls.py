"""Flower URL configuration."""

from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import (
    DashboardView,
    PlatformHomeView,
    UIKitView,
    core_health_live,
    core_health_ready,
    core_health_summary,
    core_metrics_endpoint,
    ui_kit_sample,
)

urlpatterns = [
    # -----------------------------------------------------------------------
    # Health & Monitoring
    # -----------------------------------------------------------------------
    path("health/", core_health_summary, name="health"),
    path("health/live/", core_health_live, name="health-live"),
    path("health/ready/", core_health_ready, name="health-ready"),
    path("metrics/", core_metrics_endpoint, name="metrics"),

    # -----------------------------------------------------------------------
    # Admin
    # -----------------------------------------------------------------------
    path("", PlatformHomeView.as_view(), name="platform-home"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("auth/logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path("admin/", admin.site.urls),
    path("tenants/", include("apps.tenancy.web_urls", namespace="tenancy_ui")),
    path("devices/", include("apps.devices.web_urls", namespace="devices_ui")),
    path("ui-kit/", UIKitView.as_view(), name="ui-kit"),
    path("ui-kit/sample/", ui_kit_sample, name="ui-kit-sample"),

    # -----------------------------------------------------------------------
    # API Schema & Documentation
    # -----------------------------------------------------------------------
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # -----------------------------------------------------------------------
    # Bounded Context APIs
    # -----------------------------------------------------------------------
    path("api/b2b/v1/", include("apps.provider_ops.api.urls", namespace="provider_b2b")),
    path("api/v1/tenancy/", include("apps.tenancy.api.urls", namespace="tenancy")),
    path("api/v1/identity/", include("apps.identity.api.urls", namespace="identity")),
    path("api/v1/locations/", include("apps.locations.api.urls", namespace="locations")),
    path("api/v1/plants/", include("apps.plants.api.urls", namespace="plants")),
    path("api/v1/pots/", include("apps.pots.api.urls", namespace="pots")),
    path("api/v1/devices/", include("apps.devices.api.urls", namespace="devices")),
    path("api/v1/telemetry/", include("apps.telemetry.api.urls", namespace="telemetry")),
    path("api/v1/care-engine/", include("apps.care_engine.api.urls", namespace="care_engine")),
    path("api/v1/integrations/", include("apps.integrations.api.urls", namespace="integrations")),
    path("api/v1/provider-ops/", include("apps.provider_ops.api.urls", namespace="provider_ops")),
    path("api/v1/marketplace/", include("apps.marketplace.api.urls", namespace="marketplace")),
    path("api/v1/notifications/", include("apps.notifications.api.urls", namespace="notifications")),
    path("api/v1/billing/", include("apps.billing.api.urls", namespace="billing")),
    path("api/v1/audit/", include("apps.audit.api.urls", namespace="audit")),
]

# ---------------------------------------------------------------------------
# Debug Toolbar
# ---------------------------------------------------------------------------
if settings.DEBUG:
    from django.conf.urls.static import static
    try:
        from debug_toolbar.toolbar import debug_toolbar_urls
        urlpatterns += debug_toolbar_urls()
    except ImportError:
        pass

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
