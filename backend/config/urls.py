"""PlantOps URL Configuration."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import DashboardView, UIKitView, ui_kit_sample

urlpatterns = [
    # -----------------------------------------------------------------------
    # Admin
    # -----------------------------------------------------------------------
    path("", DashboardView.as_view(), name="dashboard"),
    path("admin/", admin.site.urls),
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
    path("api/v1/telemetry/", include("apps.telemetry.api.urls", namespace="telemetry")),
    # path("api/v1/users/", include("apps.users.api.urls", namespace="users")),
    # path("api/v1/locations/", include("apps.locations.api.urls", namespace="locations")),
    # path("api/v1/planters/", include("apps.planters.api.urls", namespace="planters")),
    # path("api/v1/plants/", include("apps.plants.api.urls", namespace="plants")),
    # path("api/v1/devices/", include("apps.devices.api.urls", namespace="devices")),
    # path("api/v1/alerts/", include("apps.alerts.api.urls", namespace="alerts")),
    # path("api/v1/automation/", include("apps.automation.api.urls", namespace="automation")),
    # path("api/v1/firmware/", include("apps.firmware.api.urls", namespace="firmware")),
    # path("api/v1/tasks/", include("apps.tasks.api.urls", namespace="tasks")),
    # path("api/v1/notifications/", include("apps.notifications.api.urls", namespace="notifications")),
    # path("api/v1/billing/", include("apps.billing.api.urls", namespace="billing")),
]

# ---------------------------------------------------------------------------
# Debug Toolbar
# ---------------------------------------------------------------------------
if settings.DEBUG:
    from django.conf.urls.static import static
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += debug_toolbar_urls()
