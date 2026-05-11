from django.db import transaction
from django.utils import timezone

from apps.integrations.domain.enums import ProviderConnectionStatus
from apps.integrations.models import ProviderConnection


def create_provider_connection(
    *,
    provider_tenant_id: str,
    provider_base_url: str,
    api_key_hash: str = "",
    key_id: str = "",
    shared_secret_reference: str = "",
    scopes: list[str] | None = None,
) -> ProviderConnection:
    """Create owner-tenant metadata for a provider delivery target."""
    with transaction.atomic():
        return ProviderConnection.objects.create(
            provider_tenant_id=provider_tenant_id,
            provider_base_url=provider_base_url,
            api_key_hash=api_key_hash,
            key_id=key_id,
            shared_secret_reference=shared_secret_reference,
            scopes=scopes or [],
            status=ProviderConnectionStatus.ACTIVE,
        )


def revoke_provider_connection(*, connection: ProviderConnection) -> ProviderConnection:
    """Revoke an owner-tenant provider connection."""
    connection.status = ProviderConnectionStatus.REVOKED
    connection.revoked_at = timezone.now()
    connection.save(update_fields=["status", "revoked_at", "updated_at"])
    return connection


def get_active_provider_connections_for_event(event):
    """Return active owner-tenant provider connections eligible for an event."""
    queryset = ProviderConnection.objects.filter(status=ProviderConnectionStatus.ACTIVE)
    target_provider = getattr(event, "target_provider_schema", "")
    if target_provider:
        queryset = queryset.filter(provider_tenant_id=target_provider)
    return queryset.order_by("provider_tenant_id")
