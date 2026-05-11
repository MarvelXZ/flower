from django.urls import path

from apps.provider_ops.api.views import (
    AlertUpsertView,
    BreachedTaskListView,
    DashboardDeltaView,
    DeviceUpsertView,
    LocationUpsertView,
    OverdueTaskListView,
    ProviderTaskAddNoteView,
    ProviderTaskAssignView,
    ProviderTaskCancelView,
    ProviderTaskCompleteView,
    ProviderTaskDetailView,
    ProviderTaskListView,
    ProviderTaskStartView,
    RealtimeReplayView,
    SLASummaryView,
    SyncStatusView,
    TelemetryBatchView,
)

app_name = "provider_ops"

urlpatterns = [
    # === B2B inbound (v1) ===
    path("v1/locations/upsert/", LocationUpsertView.as_view(), name="locations-upsert"),
    path("v1/devices/upsert/", DeviceUpsertView.as_view(), name="devices-upsert"),
    path("v1/telemetry/batch/", TelemetryBatchView.as_view(), name="telemetry-batch"),
    path("v1/alerts/upsert/", AlertUpsertView.as_view(), name="alerts-upsert"),
    path("v1/sync/status/", SyncStatusView.as_view(), name="sync-status"),
    # === Provider dashboard (v1) ===
    path("v1/tasks/", ProviderTaskListView.as_view(), name="task-list"),
    path("v1/tasks/<int:pk>/", ProviderTaskDetailView.as_view(), name="task-detail"),
    path("v1/tasks/<int:pk>/assign/", ProviderTaskAssignView.as_view(), name="task-assign"),
    path("v1/tasks/<int:pk>/start/", ProviderTaskStartView.as_view(), name="task-start"),
    path("v1/tasks/<int:pk>/complete/", ProviderTaskCompleteView.as_view(), name="task-complete"),
    path("v1/tasks/<int:pk>/cancel/", ProviderTaskCancelView.as_view(), name="task-cancel"),
    path("v1/tasks/<int:pk>/notes/", ProviderTaskAddNoteView.as_view(), name="task-add-note"),
    path("v1/tasks/overdue/", OverdueTaskListView.as_view(), name="task-overdue"),
    path("v1/tasks/breached/", BreachedTaskListView.as_view(), name="task-breached"),
    path("v1/sla/summary/", SLASummaryView.as_view(), name="sla-summary"),
    path("v1/realtime/replay/", RealtimeReplayView.as_view(), name="realtime-replay"),
    path("v1/dashboard/delta/", DashboardDeltaView.as_view(), name="dashboard-delta"),
]

