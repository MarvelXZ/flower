from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.plants.models import Plant, PlantLocation, PlantType


@admin.register(PlantType)
class PlantTypeAdmin(admin.ModelAdmin):
    list_display = ["key", "name", "scientific_name", "light_requirement", "water_frequency", "is_active"]
    list_filter = ["light_requirement", "water_frequency", "is_active"]
    search_fields = ["key", "name", "scientific_name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("key", "name", "scientific_name", "description")}),
        (_("Care Requirements"), {"fields": ("light_requirement", "water_frequency", "min_temperature_c", "max_temperature_c", "min_humidity", "max_humidity", "care_profile")}),
        (_("Status"), {"fields": ("is_active",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ["name", "plant_type", "planter", "status", "planted_at", "is_active"]
    list_filter = ["status", "plant_type", "is_active", "created_at"]
    search_fields = ["name", "notes"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "plant_type", "planter")}),
        (_("Status"), {"fields": ("status", "planted_at", "is_active")}),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )


@admin.register(PlantLocation)
class PlantLocationAdmin(admin.ModelAdmin):
    list_display = ["plant", "location", "position", "assigned_at", "removed_at"]
    list_filter = ["assigned_at"]
    search_fields = ["plant__name", "location__name"]
    readonly_fields = ["assigned_at"]
