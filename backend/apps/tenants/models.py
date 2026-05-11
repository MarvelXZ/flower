from django.db import models
from django_tenants.models import DomainMixin, TenantMixin
from django.utils.translation import gettext_lazy as _


class Client(TenantMixin):
    """
    Tenant model representing a single PlantOps customer.

    Each client gets its own PostgreSQL schema with isolated data.
    The `schema_name` field is managed by django-tenants.
    """

    name = models.CharField(
        max_length=100,
        verbose_name=_("client name"),
        help_text=_("Display name of the tenant organization."),
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        verbose_name=_("slug"),
        help_text=_("URL-friendly identifier for the tenant."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
        help_text=_("Inactive tenants are excluded from routing and background jobs."),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    # django-tenants: auto_create_schema and auto_drop_schema
    auto_create_schema = True
    auto_drop_schema = True

    class Meta:
        verbose_name = _("client")
        verbose_name_plural = _("clients")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Domain(DomainMixin):
    """
    Domain model mapping hostnames to tenants.

    The `domain` field is the fully-qualified hostname (e.g., "acme.plantops.local").
    The `tenant` field links to the Client.
    """

    is_primary = models.BooleanField(
        default=True,
        verbose_name=_("primary"),
        help_text=_("Primary domain used for absolute URL generation."),
    )

    class Meta:
        verbose_name = _("domain")
        verbose_name_plural = _("domains")
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain
