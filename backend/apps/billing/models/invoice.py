from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.billing.domain.enums import InvoiceStatus


class Invoice(models.Model):
    """A billing invoice for a tenant."""

    tenant_id = models.CharField(max_length=120, verbose_name=_("tenant ID"))
    subscription = models.ForeignKey(
        "billing.TenantSubscription",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoices",
        verbose_name=_("subscription"),
    )
    status = models.CharField(
        max_length=16, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT,
        verbose_name=_("status"),
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("subtotal"))
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name=_("tax amount"),
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("total amount"))
    currency = models.CharField(max_length=3, default="EUR", verbose_name=_("currency"))
    issued_at = models.DateTimeField(verbose_name=_("issued at"))
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_("paid at"))
    stripe_invoice_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("stripe invoice ID"),
    )
    pdf_url = models.URLField(max_length=512, null=True, blank=True, verbose_name=_("PDF URL"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("invoice")
        verbose_name_plural = _("invoices")
        ordering = ["-issued_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"Invoice#{self.pk}:{self.status}"
