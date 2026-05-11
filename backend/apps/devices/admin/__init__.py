from django.contrib import admin

from apps.devices.models import Device, DeviceCredential


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ["name", "uuid", "owner_tenant_schema", "status", "is_active", "last_seen_at"]
    list_filter = ["status", "is_active", "owner_tenant_schema"]
    search_fields = ["name", "uuid", "owner_tenant_schema"]


@admin.register(DeviceCredential)
class DeviceCredentialAdmin(admin.ModelAdmin):
    list_display = ["device", "api_key", "is_active", "last_used_at"]
    list_filter = ["is_active"]
    search_fields = ["device__name", "api_key"]
