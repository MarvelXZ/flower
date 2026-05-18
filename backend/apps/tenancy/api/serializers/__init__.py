
from rest_framework import serializers

from apps.tenancy.domain.enums import TenantKind
from apps.tenancy.models import Client, Domain


class TenantListSerializer(serializers.ModelSerializer):
    """Compact tenant representation for platform/admin screens."""

    primary_domain = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "slug",
            "schema_name",
            "kind",
            "is_active",
            "primary_domain",
            "created_at",
            "updated_at",
        ]

    def get_primary_domain(self, obj: Client) -> str:
        domain = obj.domains.filter(is_primary=True).first()
        return domain.domain if domain else ""


class TenantCreateSerializer(serializers.Serializer):
    """Validate the first slice of tenant onboarding."""

    name = serializers.CharField(max_length=150)
    slug = serializers.SlugField(max_length=80)
    schema_name = serializers.RegexField(
        regex=r"^[a-z][a-z0-9_]*$",
        max_length=63,
        help_text="PostgreSQL schema name. Use lowercase letters, numbers, and underscores.",
    )
    domain = serializers.CharField(max_length=253)
    kind = serializers.ChoiceField(choices=TenantKind.choices, default=TenantKind.OWNER)

    def validate_slug(self, value: str) -> str:
        if Client.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Tenant slug already exists.")
        return value

    def validate_schema_name(self, value: str) -> str:
        if value == "public":
            raise serializers.ValidationError("The public schema is reserved.")
        if Client.objects.filter(schema_name=value).exists():
            raise serializers.ValidationError("Tenant schema already exists.")
        return value

    def validate_domain(self, value: str) -> str:
        domain = value.strip().lower()
        if not domain:
            raise serializers.ValidationError("Domain is required.")
        if "/" in domain or ":" in domain:
            raise serializers.ValidationError("Use a hostname only, without protocol or path.")
        if Domain.objects.filter(domain=domain).exists():
            raise serializers.ValidationError("Tenant domain already exists.")
        return domain
