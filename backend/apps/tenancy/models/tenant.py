from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.models import TenantMixin

from apps.tenancy.domain.enums import TenantKind


class Client(TenantMixin):
    """Tenant compatible with django-tenants."""

    name = models.CharField(max_length=150, verbose_name=_("name"))
    slug = models.SlugField(max_length=80, unique=True, verbose_name=_("slug"))
    kind = models.CharField(
        max_length=32,
        choices=TenantKind.choices,
        default=TenantKind.OWNER,
        verbose_name=_("tenant kind"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        verbose_name = _("client")
        verbose_name_plural = _("clients")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
