from django.db import models
from django.utils.translation import gettext_lazy as _


class ProviderProfileStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")


class ListingStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    PAUSED = "paused", _("Paused")
    ARCHIVED = "archived", _("Archived")


class ListingType(models.TextChoices):
    SERVICE = "service", _("Service")
    SUBSCRIPTION = "subscription", _("Subscription")
    PRODUCT = "product", _("Product")


class PricingModel(models.TextChoices):
    FIXED = "fixed", _("Fixed")
    MONTHLY = "monthly", _("Monthly")
    YEARLY = "yearly", _("Yearly")
    USAGE_BASED = "usage_based", _("Usage based")


class OfferStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")
    EXPIRED = "expired", _("Expired")
    CANCELLED = "cancelled", _("Cancelled")


class ServiceOrderStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
