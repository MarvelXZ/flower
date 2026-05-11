from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.telemetry.models import SensorType, TelemetryRecord, TelemetryBatch


@admin.register(SensorType)
class SensorTypeAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "unit", "min_value", "max_value"]
    search_fields = ["key", "name"]


@admin.register(TelemetryRecord)
class TelemetryRecordAdmin(admin.ModelAdmin):
    list_display = ["device", "sensor_type", "value", "measured_at", "received_at", "is_valid"]
    list_filter = ["sensor_type", "is_valid", "received_at"]
    search_fields = ["device__device_id", "message_id"]
    readonly_fields = ["received_at"]
    date_hierarchy = "measured_at"


@admin.register(TelemetryBatch)
class TelemetryBatchAdmin(admin.ModelAdmin):
    list_display = ["device", "sensor_type", "period_start", "period_end", "avg_value", "record_count"]
    list_filter = ["sensor_type"]
    readonly_fields = ["created_at", "updated_at"]
