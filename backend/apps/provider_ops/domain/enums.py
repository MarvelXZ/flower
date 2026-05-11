from django.db import models
from django.utils.translation import gettext_lazy as _


class InboundKeyStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    DISABLED = "disabled", _("Disabled")
    REVOKED = "revoked", _("Revoked")


class ProviderTaskType(models.TextChoices):
    INSPECTION = "inspection", _("Inspection")
    WATERING = "watering", _("Watering")
    DEVICE_CHECK = "device_check", _("Device check")
    REPLACEMENT = "replacement", _("Replacement")
    MAINTENANCE = "maintenance", _("Maintenance")
    OTHER = "other", _("Other")


class ProviderTaskPriority(models.TextChoices):
    LOW = "low", _("Low")
    NORMAL = "normal", _("Normal")
    HIGH = "high", _("High")
    URGENT = "urgent", _("Urgent")


class ProviderTaskStatus(models.TextChoices):
    OPEN = "open", _("Open")
    ASSIGNED = "assigned", _("Assigned")
    IN_PROGRESS = "in_progress", _("In progress")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class ProviderTaskEventType(models.TextChoices):
    CREATED = "created", _("Created")
    ASSIGNED = "assigned", _("Assigned")
    STARTED = "started", _("Started")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")
    NOTE_ADDED = "note_added", _("Note added")


class TaskEscalationType(models.TextChoices):
    RESPONSE_SLA_BREACH = "response_sla_breach", _("Response SLA breach")
    RESOLUTION_SLA_BREACH = "resolution_sla_breach", _("Resolution SLA breach")
    OVERDUE = "overdue", _("Overdue")
    REASSIGNMENT = "reassignment", _("Reassignment")
    PRIORITY_UPGRADE = "priority_upgrade", _("Priority upgrade")
    REMINDER_SENT = "reminder_sent", _("Reminder sent")
