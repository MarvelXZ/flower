from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.locations.models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "location_type", "address", "timezone", "is_active"]
    list_filter = ["location_type", "is_active", "created_at"]
    search_fields = ["name", "address", "description"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "description", "address")}),
        (_("Geography"), {"fields": ("latitude", "longitude", "timezone")}),
        (_("Type"), {"fields": ("location_type", "is_active")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )
