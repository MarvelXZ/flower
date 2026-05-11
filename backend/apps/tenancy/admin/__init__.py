from django.contrib import admin

from apps.tenancy.models import Client, Domain


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "schema_name", "kind", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name", "slug", "schema_name"]


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ["domain", "tenant", "is_primary"]
    list_filter = ["is_primary"]
    search_fields = ["domain", "tenant__name"]
