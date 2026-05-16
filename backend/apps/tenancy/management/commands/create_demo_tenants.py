from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client, Domain


@dataclass(frozen=True)
class DemoTenant:
    name: str
    slug: str
    schema_name: str
    kind: str
    domain: str


DEMO_TENANTS = (
    DemoTenant(
        name="Tenant 1",
        slug="tenant1",
        schema_name="tenant1",
        kind=TenantKind.OWNER,
        domain="tenant1.localhost",
    ),
    DemoTenant(
        name="Tenant 2",
        slug="tenant2",
        schema_name="tenant2",
        kind=TenantKind.OWNER,
        domain="tenant2.localhost",
    ),
    DemoTenant(
        name="Demo Owner",
        slug="owner",
        schema_name="owner",
        kind=TenantKind.OWNER,
        domain="owner.localhost",
    ),
    DemoTenant(
        name="Demo Provider",
        slug="provider",
        schema_name="provider",
        kind=TenantKind.PROVIDER,
        domain="provider.localhost",
    ),
    DemoTenant(
        name="Demo Hybrid",
        slug="hybrid",
        schema_name="hybrid",
        kind=TenantKind.HYBRID,
        domain="hybrid.localhost",
    ),
)


class Command(BaseCommand):
    help = "Create demo owner, provider, and hybrid tenants for local development."

    def handle(self, *args, **options):
        created_count = 0

        for definition in DEMO_TENANTS:
            with transaction.atomic():
                tenant, created = Client.objects.get_or_create(
                    schema_name=definition.schema_name,
                    defaults={
                        "name": definition.name,
                        "slug": definition.slug,
                        "kind": definition.kind,
                    },
                )

                if not created:
                    tenant.name = definition.name
                    tenant.slug = definition.slug
                    tenant.kind = definition.kind
                    tenant.is_active = True
                    tenant.save(update_fields=["name", "slug", "kind", "is_active", "updated_at"])

                Domain.objects.update_or_create(
                    domain=definition.domain,
                    defaults={
                        "tenant": tenant,
                        "is_primary": True,
                    },
                )

            created_count += int(created)
            state = "created" if created else "updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{state}: {definition.schema_name} ({definition.kind}) -> {definition.domain}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Demo tenants ready; created={created_count}."))
