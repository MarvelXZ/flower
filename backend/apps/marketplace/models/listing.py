from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.marketplace.domain.enums import ListingStatus, ListingType, PricingModel


class ProviderListing(models.Model):
    """A service, subscription, or product offered by a provider tenant."""

    provider_tenant_id = models.CharField(
        max_length=120, verbose_name=_("provider tenant ID"),
    )
    listing_type = models.CharField(
        max_length=16, choices=ListingType.choices, verbose_name=_("listing type"),
    )
    status = models.CharField(
        max_length=16, choices=ListingStatus.choices, default=ListingStatus.DRAFT,
        verbose_name=_("status"),
    )
    title = models.CharField(max_length=255, verbose_name=_("title"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    short_description = models.CharField(
        max_length=255, blank=True, verbose_name=_("short description"),
    )
    category = models.CharField(max_length=64, blank=True, verbose_name=_("category"))
    tags = models.JSONField(default=list, blank=True, verbose_name=_("tags"))
    pricing_model = models.CharField(
        max_length=16, choices=PricingModel.choices, verbose_name=_("pricing model"),
    )
    base_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_("base price"),
    )
    currency = models.CharField(
        max_length=3, default="EUR", verbose_name=_("currency"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    is_public = models.BooleanField(default=True, verbose_name=_("public"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("provider listing")
        verbose_name_plural = _("provider listings")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider_tenant_id", "status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider_tenant_id}:{self.title}"


class ProviderServiceArea(models.Model):
    """Geographic area where a listing is available."""

    listing = models.ForeignKey(
        ProviderListing, on_delete=models.CASCADE,
        related_name="service_areas", verbose_name=_("listing"),
    )
    country = models.CharField(max_length=4, verbose_name=_("country"))
    city = models.CharField(max_length=120, null=True, blank=True, verbose_name=_("city"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("provider service area")
        verbose_name_plural = _("provider service areas")
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "country", "city"],
                name="unique_listing_area",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.listing_id}:{self.country}/{self.city or '*'}"
