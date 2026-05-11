from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.planters.models import Planter


@admin.register(Planter)
class PlanterAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "location", "device", "material", "status", "is_active"]
    list_filter = ["status", "material", "is_active", "created_at"]
    search_fields = ["name", "code"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "code")}),
        (_("Assignment"), {"fields": ("location", "device")}),
        (_("Physical"), {"fields": ("material", "dimensions")}),
        (_("Status"), {"fields": ("status", "is_active", "notes")}),
        (_("Timestamps"), {"fields": ("created_at", "updated_at", "created_by", "updated_by")}),
    )
