from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.devices.models import Device, DeviceCredential, DeviceHeartbeat, DeviceProvisioningToken


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "device_id", "device_type", "status", "firmware_version", "last_seen_at", "is_active"]
    list_filter = ["status", "device_type", "is_active", "created_at"]
    search_fields = ["name", "device_id"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "device_id", "device_type")}),
        (_("Status"), {"fields": ("status", "firmware_version", "battery_level", "last_seen_at", "is_active")}),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(DeviceCredential)
class DeviceCredentialAdmin(admin.ModelAdmin):
    list_display = ["device", "api_key", "is_active", "last_used_at"]
    list_filter = ["is_active"]
    search_fields = ["device__name", "api_key"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DeviceProvisioningToken)
class DeviceProvisioningTokenAdmin(admin.ModelAdmin):
    list_display = ["device_id", "is_used", "expires_at", "created_at"]
    list_filter = ["is_used"]
    search_fields = ["device_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(DeviceHeartbeat)
class DeviceHeartbeatAdmin(admin.ModelAdmin):
    list_display = ["device", "firmware_version", "uptime_seconds", "free_heap_kb", "wifi_rssi", "reported_at"]
    list_filter = ["reported_at"]
    search_fields = ["device__name", "device__device_id"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "reported_at"
