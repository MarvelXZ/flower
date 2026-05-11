"""
Billing bounded context.

Responsible for subscriptions, invoices, payments, and usage metering.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditableModel


class Subscription(AuditableModel):
    """
    A tenant's subscription plan.

    Tracks plan type, billing cycle, and usage limits.
    Stripe integration is a future concern.
    """

    class Plan(models.TextChoices):
        FREE = "free", _("Free")
        BASIC = "basic", _("Basic")
        PRO = "pro", _("Pro")
        ENTERPRISE = "enterprise", _("Enterprise")

    class BillingCycle(models.TextChoices):
        MONTHLY = "monthly", _("Monthly")
        YEARLY = "yearly", _("Yearly")

    plan = models.CharField(
        max_length=20,
        choices=Plan.choices,
        default=Plan.FREE,
        verbose_name=_("plan"),
    )
    billing_cycle = models.CharField(
        max_length=10,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        verbose_name=_("billing cycle"),
    )
    start_date = models.DateField(
        verbose_name=_("start date"),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("end date"),
    )
    max_devices = models.PositiveIntegerField(
        default=5,
        verbose_name=_("max devices"),
    )
    max_planters = models.PositiveIntegerField(
        default=10,
        verbose_name=_("max planters"),
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Stripe subscription ID"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    class Meta:
        verbose_name = _("subscription")
        verbose_name_plural = _("subscriptions")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.plan} ({self.billing_cycle})"
