from django.contrib import admin

from apps.integrations.models import IntegrationOutbox, OutboxDelivery, ProviderConnection, ProviderKey


@admin.register(IntegrationOutbox)
class IntegrationOutboxAdmin(admin.ModelAdmin):
    list_display = ["event_type", "aggregate_type", "aggregate_id", "status", "attempts", "created_at"]
    list_filter = ["status", "event_type"]
    search_fields = ["aggregate_id", "idempotency_key", "target_provider_schema"]


@admin.register(OutboxDelivery)
class OutboxDeliveryAdmin(admin.ModelAdmin):
    list_display = ["outbox", "status", "response_code", "delivered_at", "created_at"]
    list_filter = ["status", "response_code"]


@admin.register(ProviderConnection)
class ProviderConnectionAdmin(admin.ModelAdmin):
    list_display = ["provider_tenant_id", "provider_base_url", "key_id", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["provider_tenant_id", "provider_base_url", "key_id"]


@admin.register(ProviderKey)
class ProviderKeyAdmin(admin.ModelAdmin):
    list_display = ["key_id", "provider_connection", "status", "valid_from", "valid_until"]
    list_filter = ["status"]
    search_fields = ["key_id", "provider_connection__provider_tenant_id"]
