from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.marketplace.domain.enums import ServiceOrderStatus


class ServiceOrder(models.Model):
    """An order placed by an owner tenant for a provider service."""

    owner_tenant_id = models.CharField(
        max_length=120, verbose_name=_("owner tenant ID"),
    )
    provider_tenant_id = models.CharField(
        max_length=120, verbose_name=_("provider tenant ID"),
    )
    listing = models.ForeignKey(
        "marketplace.ProviderListing",
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name=_("listing"),
    )
    marketplace_offer = models.ForeignKey(
        "marketplace.MarketplaceOffer",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="orders",
        verbose_name=_("marketplace offer"),
    )
    status = models.CharField(
        max_length=16, choices=ServiceOrderStatus.choices, default=ServiceOrderStatus.PENDING,
        verbose_name=_("status"),
    )
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name=_("total amount"),
    )
    currency = models.CharField(max_length=3, default="EUR", verbose_name=_("currency"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    ordered_at = models.DateTimeField(auto_now_add=True, verbose_name=_("ordered at"))
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("completed at"),
    )

    class Meta:
        verbose_name = _("service order")
        verbose_name_plural = _("service orders")
        ordering = ["-ordered_at"]
        indexes = [
            models.Index(fields=["owner_tenant_id", "status"]),
            models.Index(fields=["provider_tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"Order#{self.pk}:{self.status}"
