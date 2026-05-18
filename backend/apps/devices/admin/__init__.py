from django.contrib import admin
from django.urls import path

from apps.devices.platform_views import PlatformDeviceFleetView, PlatformDeviceProvisionView
from apps.devices.models import Device, DeviceCredential


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "uuid", "owner_tenant_schema", "status", "is_active", "last_seen_at"]
    list_filter = ["status", "is_active", "owner_tenant_schema"]
    search_fields = ["name", "uuid", "owner_tenant_schema"]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "fleet/",
                self.admin_site.admin_view(PlatformDeviceFleetView.as_view()),
                name="devices_device_fleet",
            ),
            path(
                "provision/",
                self.admin_site.admin_view(PlatformDeviceProvisionView.as_view()),
                name="devices_device_provision",
            ),
        ]
        return custom_urls + urls


@admin.register(DeviceCredential)
class DeviceCredentialAdmin(admin.ModelAdmin):
    list_display = ["device", "api_key", "is_active", "last_used_at"]
    list_filter = ["is_active"]
    search_fields = ["device__name", "api_key"]
