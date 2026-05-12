from django.db import models
from django.utils.translation import gettext_lazy as _


class AlertSeverity(models.TextChoices):
    INFO = "info", _("Info")
    WARNING = "warning", _("Warning")
    CRITICAL = "critical", _("Critical")


class AlertStatus(models.TextChoices):
    OPEN = "open", _("Open")
    ACKNOWLEDGED = "acknowledged", _("Acknowledged")
    RESOLVED = "resolved", _("Resolved")
    DISMISSED = "dismissed", _("Dismissed")
    SUPPRESSED = "suppressed", _("Suppressed")


class AlertSourceType(models.TextChoices):
    SENSOR_READING = "sensor_reading", _("Sensor reading")
    DEVICE = "device", _("Device")
    PLANT = "plant", _("Plant")
    SYSTEM = "system", _("System")


class NotificationType(models.TextChoices):
    ALERT_CREATED = "alert_created", _("Alert created")
    ALERT_UPDATED = "alert_updated", _("Alert updated")
    ALERT_RESOLVED = "alert_resolved", _("Alert resolved")


class NotificationChannel(models.TextChoices):
    PUSH = "push", _("Push")
    EMAIL = "email", _("Email")
    SMS = "sms", _("SMS")
    IN_APP = "in_app", _("In-app")
    WEBHOOK = "webhook", _("Webhook")


class NotificationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    PROCESSING = "processing", _("Processing")
    SENT = "sent", _("Sent")
    RETRY = "retry", _("Retry")
    FAILED = "failed", _("Failed")
    DEAD_LETTER = "dead_letter", _("Dead letter")


class RecipientType(models.TextChoices):
    USER = "user", _("User")
    TENANT = "tenant", _("Tenant")
    PROVIDER = "provider", _("Provider")
    SYSTEM = "system", _("System")
