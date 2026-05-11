from django.db import models
from django.utils.translation import gettext_lazy as _


class BillingStatus(models.TextChoices):
    TRIAL = "trial", _("Trial")
    ACTIVE = "active", _("Active")
    PAST_DUE = "past_due", _("Past due")
    CANCELED = "canceled", _("Canceled")


class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    PAST_DUE = "past_due", _("Past due")
    CANCELLED = "cancelled", _("Cancelled")
    TRIALING = "trialing", _("Trialing")
    EXPIRED = "expired", _("Expired")


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    OPEN = "open", _("Open")
    PAID = "paid", _("Paid")
    VOID = "void", _("Void")
    UNCOLLECTIBLE = "uncollectible", _("Uncollectible")


class BillingInterval(models.TextChoices):
    MONTHLY = "monthly", _("Monthly")
    YEARLY = "yearly", _("Yearly")
