from django.db import transaction

from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client, Domain


def create_tenant(
    *,
    name: str,
    slug: str,
    schema_name: str,
    domain: str,
    kind: str = TenantKind.OWNER,
) -> Client:
    """Create a tenant and its primary domain."""
    with transaction.atomic():
        tenant = Client.objects.create(
            name=name,
            slug=slug,
            schema_name=schema_name,
            kind=kind,
        )
        Domain.objects.create(tenant=tenant, domain=domain, is_primary=True)
    return tenant
