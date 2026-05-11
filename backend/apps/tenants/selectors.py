"""
Tenant read operations (selectors layer).

All queries for tenant data MUST go through this module.
This keeps read logic centralized and testable.
"""

from django.db.models import QuerySet

from apps.tenants.models import Client, Domain


def get_active_tenants() -> QuerySet[Client]:
    """Return all active tenants."""
    return Client.objects.filter(is_active=True)


def get_tenant_by_slug(*, slug: str) -> Client | None:
    """Return a tenant by its slug, or None."""
    return Client.objects.filter(slug=slug, is_active=True).first()


def get_tenant_domains(*, tenant: Client) -> QuerySet[Domain]:
    """Return all domains for a given tenant."""
    return Domain.objects.filter(tenant=tenant)
