from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.marketplace.domain.enums import OfferStatus


class MarketplaceOffer(models.Model):
    """An owner tenant's offer on a provider listing."""

    owner_tenant_id = models.CharField(
        max_length=120, verbose_name=_("owner tenant ID"),
    )
    provider_tenant_id = models.CharField(
        max_length=120, verbose_name=_("provider tenant ID"),
    )
    listing = models.ForeignKey(
        "marketplace.ProviderListing",
        on_delete=models.CASCADE,
        related_name="offers",
        verbose_name=_("listing"),
    )
    status = models.CharField(
        max_length=16, choices=OfferStatus.choices, default=OfferStatus.PENDING,
        verbose_name=_("status"),
    )
    offered_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_("offered price"),
    )
    currency = models.CharField(max_length=3, default="EUR", verbose_name=_("currency"))
    message = models.TextField(blank=True, verbose_name=_("message"))
    valid_until = models.DateTimeField(
        null=True, blank=True, verbose_name=_("valid until"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    responded_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("responded at"),
    )

    class Meta:
        verbose_name = _("marketplace offer")
        verbose_name_plural = _("marketplace offers")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner_tenant_id", "status"]),
            models.Index(fields=["listing", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner_tenant_id}→{self.listing_id}"
