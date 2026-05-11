from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.marketplace.domain.enums import ProviderProfileStatus


class MarketplaceProviderProfile(models.Model):
    """Public provider profile for marketplace discovery."""

    provider_tenant_schema = models.CharField(
        max_length=63,
        unique=True,
        verbose_name=_("provider tenant schema"),
    )
    display_name = models.CharField(max_length=180, verbose_name=_("display name"))
    slug = models.SlugField(max_length=200, unique=True, verbose_name=_("slug"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    status = models.CharField(
        max_length=32,
        choices=ProviderProfileStatus.choices,
        default=ProviderProfileStatus.DRAFT,
        verbose_name=_("status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("marketplace provider profile")
        verbose_name_plural = _("marketplace provider profiles")
        ordering = ["display_name"]

    def __str__(self) -> str:
        return self.display_name
