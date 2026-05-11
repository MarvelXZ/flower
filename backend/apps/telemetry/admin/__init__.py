from django.contrib import admin

from apps.telemetry.models import SensorReading


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ["device", "measured_at", "soil_moisture", "temperature", "battery_level"]
    list_filter = ["measured_at"]
    search_fields = ["device__name", "device__uuid"]
    readonly_fields = ["created_at"]
