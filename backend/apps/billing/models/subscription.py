from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.billing.domain.enums import SubscriptionStatus


class TenantSubscription(models.Model):
    """A tenant's active (or historical) subscription."""

    tenant_id = models.CharField(max_length=120, verbose_name=_("tenant ID"))
    subscription_plan = models.ForeignKey(
        "billing.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        related_name="tenant_subscriptions",
        verbose_name=_("subscription plan"),
    )
    status = models.CharField(
        max_length=16, choices=SubscriptionStatus.choices, default=SubscriptionStatus.ACTIVE,
        verbose_name=_("status"),
    )
    started_at = models.DateTimeField(verbose_name=_("started at"))
    current_period_start = models.DateTimeField(verbose_name=_("current period start"))
    current_period_end = models.DateTimeField(verbose_name=_("current period end"))
    cancelled_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("cancelled at"),
    )
    stripe_customer_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("stripe customer ID"),
    )
    stripe_subscription_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("stripe subscription ID"),
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("tenant subscription")
        verbose_name_plural = _("tenant subscriptions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.subscription_plan_id}"
