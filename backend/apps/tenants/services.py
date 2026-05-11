"""
Tenant write operations (services layer).

All mutations to tenant data MUST go through this module.
Direct model writes outside of services are prohibited.
"""

from django.db import transaction

from apps.tenants.models import Client, Domain


def create_tenant(
    *,
    name: str,
    slug: str,
    schema_name: str,
    domain: str,
    description: str = "",
) -> Client:
    """
    Create a new tenant with its schema and primary domain.

    This is the ONLY sanctioned way to provision a new tenant.
    """
    with transaction.atomic():
        tenant = Client.objects.create(
            name=name,
            slug=slug,
            schema_name=schema_name,
            description=description,
        )
        Domain.objects.create(
            tenant=tenant,
            domain=domain,
            is_primary=True,
        )
    return tenant


def deactivate_tenant(*, tenant: Client) -> None:
    """Soft-deactivate a tenant."""
    tenant.is_active = False
    tenant.save(update_fields=["is_active", "updated_at"])
