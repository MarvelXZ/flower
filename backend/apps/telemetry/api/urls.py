"""
Telemetry API URLs.
"""

from django.urls import path

from apps.telemetry.views import TelemetryIngestView

app_name = "telemetry"

urlpatterns = [
    path("ingest/", TelemetryIngestView.as_view(), name="telemetry-ingest"),
]
