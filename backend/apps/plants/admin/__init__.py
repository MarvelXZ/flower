from django.contrib import admin

from apps.plants.models import Plant


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ["name", "species", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["name", "species__name"]
