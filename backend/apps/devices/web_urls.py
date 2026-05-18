from django.urls import path

from apps.devices.platform_views import PlatformDeviceFleetView, PlatformDeviceProvisionView

app_name = "devices_ui"

urlpatterns = [
    path("", PlatformDeviceFleetView.as_view(), name="device-fleet"),
    path("provision/", PlatformDeviceProvisionView.as_view(), name="device-provision"),
]
