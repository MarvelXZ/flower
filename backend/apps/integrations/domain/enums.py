from django.db import models
from django.utils.translation import gettext_lazy as _


class OutboxStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    PROCESSED = "processed", _("Processed")
    RETRY = "retry", _("Retry")
    DEAD_LETTER = "dead_letter", _("Dead letter")


class ProviderConnectionStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    DISABLED = "disabled", _("Disabled")
    REVOKED = "revoked", _("Revoked")


class ProviderKeyStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    DISABLED = "disabled", _("Disabled")
    REVOKED = "revoked", _("Revoked")
    ROTATED = "rotated", _("Rotated")


class ProviderScope(models.TextChoices):
    TELEMETRY_WRITE = "telemetry:write", _("Telemetry write")
    LOCATIONS_WRITE = "locations:write", _("Locations write")
    DEVICES_WRITE = "devices:write", _("Devices write")


class EngagementStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    ACTIVE = "active", _("Active")
    SUSPENDED = "suspended", _("Suspended")
    REVOKED = "revoked", _("Revoked")


class SyncRunType(models.TextChoices):
    FULL = "full", _("Full")
    DELTA = "delta", _("Delta")
    RESYNC = "resync", _("Resync")


class SyncRunStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    RUNNING = "running", _("Running")
    COMPLETED = "completed", _("Completed")
    FAILED = "failed", _("Failed")
    CANCELLED = "cancelled", _("Cancelled")


class SyncItemStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSED = "processed", _("Processed")
    FAILED = "failed", _("Failed")
    SKIPPED = "skipped", _("Skipped")
