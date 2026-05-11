from django.contrib import admin

from apps.alerts.models import Alert, AlertEvent, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "sensor_type", "condition", "threshold", "severity", "is_active"]
    list_filter = ["condition", "severity", "is_active"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["device", "severity", "message", "is_active", "acknowledged_by", "resolved_at", "created_at"]
    list_filter = ["severity", "is_active", "created_at"]
    search_fields = ["message", "device__name", "device__device_id"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ["alert", "event_type", "actor", "occurred_at"]
    list_filter = ["event_type", "occurred_at"]
    readonly_fields = ["occurred_at"]
