from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.tenants.models import Client, Domain


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "schema_name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "slug", "schema_name"]
    readonly_fields = ["created_at", "updated_at"]
    fieldsets = (
        (None, {"fields": ("name", "slug", "schema_name", "description")}),
        (_("Status"), {"fields": ("is_active", "created_at", "updated_at")}),
    )


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "tenant", "is_primary"]
    list_filter = ["is_primary"]
    search_fields = ["domain", "tenant__name"]
    autocomplete_fields = ["tenant"]
