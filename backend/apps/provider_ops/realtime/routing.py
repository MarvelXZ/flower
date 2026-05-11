"""WebSocket routing for the provider dashboard."""

from django.urls import re_path

from apps.provider_ops.realtime.consumers import DashboardConsumer

websocket_urlpatterns = [
    re_path(r"ws/provider/v1/dashboard/$", DashboardConsumer.as_asgi()),
]
