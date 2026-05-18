from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client, Domain


class Command(BaseCommand):
    help = "Ensure localhost resolves to the public/platform tenant in local development."

    def handle(self, *args, **options):
        with transaction.atomic():
            tenant, created = Client.objects.get_or_create(
                schema_name="public",
                defaults={
                    "name": "Flower Platform",
                    "slug": "platform",
                    "kind": TenantKind.MARKETPLACE_ADMIN,
                },
            )

            if not created:
                tenant.name = tenant.name or "Flower Platform"
                tenant.slug = tenant.slug or "platform"
                tenant.kind = tenant.kind or TenantKind.MARKETPLACE_ADMIN
                tenant.is_active = True
                tenant.save(update_fields=["name", "slug", "kind", "is_active", "updated_at"])

            Domain.objects.update_or_create(
                domain="localhost",
                defaults={
                    "tenant": tenant,
                    "is_primary": True,
                },
            )

        state = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"{state}: localhost -> {tenant.schema_name}"))
