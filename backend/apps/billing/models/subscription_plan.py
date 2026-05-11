from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.billing.domain.enums import BillingInterval


class SubscriptionPlan(models.Model):
    """A billable subscription plan with feature limits."""

    code = models.CharField(max_length=64, unique=True, verbose_name=_("code"))
    name = models.CharField(max_length=180, verbose_name=_("name"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    billing_interval = models.CharField(
        max_length=16, choices=BillingInterval.choices, verbose_name=_("billing interval"),
    )
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("price"))
    currency = models.CharField(max_length=3, default="EUR", verbose_name=_("currency"))
    max_devices = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("max devices"))
    max_users = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("max users"))
    max_locations = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("max locations"))
    features = models.JSONField(default=list, blank=True, verbose_name=_("features"))
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("subscription plan")
        verbose_name_plural = _("subscription plans")
        ordering = ["price"]

    def __str__(self) -> str:
        return self.code
