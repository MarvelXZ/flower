from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.firmware.models import FirmwareVersion, FirmwareUpdate


@admin.register(FirmwareVersion)
class FirmwareVersionAdmin(admin.ModelAdmin):
    list_display = ["version", "device_type", "is_stable", "created_at"]
    list_filter = ["device_type", "is_stable", "created_at"]
    search_fields = ["version", "changelog"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("version", "device_type", "binary")}),
        (_("Details"), {"fields": ("changelog", "is_stable")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(FirmwareUpdate)
class FirmwareUpdateAdmin(admin.ModelAdmin):
    list_display = ["device", "target_version", "status", "progress_percent", "started_at", "completed_at"]
    list_filter = ["status", "started_at"]
    search_fields = ["device__name", "device__device_id"]
    readonly_fields = ["started_at"]
    fieldsets = (
        (None, {"fields": ("device", "target_version", "status")}),
        (_("Progress"), {"fields": ("progress_percent", "error_message")}),
        (_("Timestamps"), {"fields": ("started_at", "completed_at")}),
    )
