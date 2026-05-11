from django.contrib import admin

from apps.marketplace.models import MarketplaceProviderProfile


@admin.register(MarketplaceProviderProfile)
class MarketplaceProviderProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "provider_tenant_schema", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["display_name", "slug", "provider_tenant_schema"]
    prepopulated_fields = {"slug": ("display_name",)}
