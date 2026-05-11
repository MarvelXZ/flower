from django.contrib import admin

from apps.locations.models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "address", "timezone"]
    list_filter = ["kind", "timezone"]
    search_fields = ["name", "address"]
