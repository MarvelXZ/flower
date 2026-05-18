import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import tenant_context

from apps.tenancy.models import Client


class Command(BaseCommand):
    help = "Create or update a superuser inside a tenant schema."

    def add_arguments(self, parser):
        parser.add_argument("--tenant", required=True, help="Tenant schema name, e.g. tenant1.")
        parser.add_argument("--username", default="admin")
        parser.add_argument("--email", default="admin@example.test")
        parser.add_argument(
            "--password",
            default=os.environ.get("DJANGO_SUPERUSER_PASSWORD", ""),
            help="Password for local/dev bootstrap. Can also use DJANGO_SUPERUSER_PASSWORD.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError("Password is required. Pass --password or set DJANGO_SUPERUSER_PASSWORD.")

        try:
            tenant = Client.objects.get(schema_name=options["tenant"])
        except Client.DoesNotExist as exc:
            raise CommandError(f"Tenant '{options['tenant']}' does not exist.") from exc

        User = get_user_model()
        with tenant_context(tenant):
            user, created = User.objects.get_or_create(
                username=options["username"],
                defaults={
                    "email": options["email"],
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            user.email = options["email"]
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.set_password(password)
            user.save()

        state = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{state}: {options['username']} is superuser in tenant '{tenant.schema_name}'"
            )
        )
