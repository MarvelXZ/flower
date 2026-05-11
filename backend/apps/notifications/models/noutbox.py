import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.domain.enums import (
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    RecipientType,
)


class NotificationOutbox(models.Model):
    """Tenant-local outbox for asynchronous notification delivery.

    Created by the alert service when alerts change state.  A delivery
    worker picks up pending records and sends them through a replaceable
    transport (mock, FCM, APNs, email, etc.).
    """

    event_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("event ID"),
        help_text=_("Stable idempotency key for deduplication."),
    )
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
        verbose_name=_("notification type"),
    )
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
        verbose_name=_("channel"),
    )
    recipient_type = models.CharField(
        max_length=16,
        choices=RecipientType.choices,
        default=RecipientType.TENANT,
        verbose_name=_("recipient type"),
    )
    recipient_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("recipient ID"),
    )
    alert = models.ForeignKey(
        "notifications.Alert",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="notification_outbox",
        verbose_name=_("alert"),
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name=_("payload"))
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        verbose_name=_("status"),
    )
    attempt_count = models.PositiveIntegerField(default=0, verbose_name=_("attempt count"))
    available_at = models.DateTimeField(default=timezone.now, verbose_name=_("available at"))
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("sent at"))
    failed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("failed at"))
    last_error = models.TextField(blank=True, verbose_name=_("last error"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("notification outbox")
        verbose_name_plural = _("notification outboxes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["notification_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type}:{self.status}"


class NotificationDelivery(models.Model):
    """Delivery attempt for a NotificationOutbox."""

    notification = models.ForeignKey(
        NotificationOutbox,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("notification"),
    )
    attempt_number = models.PositiveIntegerField(verbose_name=_("attempt number"))
    status = models.CharField(
        max_length=16,
        choices=NotificationStatus.choices,
        verbose_name=_("status"),
    )
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannel.choices,
        verbose_name=_("channel"),
    )
    error = models.TextField(blank=True, verbose_name=_("error"))
    provider_response = models.JSONField(
        default=dict, blank=True, verbose_name=_("provider response"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("notification delivery")
        verbose_name_plural = _("notification deliveries")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notification", "attempt_number"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_id}:{self.status}"


class NotificationPreference(models.Model):
    """Per-recipient channel preference for notification delivery."""

    recipient_type = models.CharField(
        max_length=16,
        choices=RecipientType.choices,
        verbose_name=_("recipient type"),
    )
    recipient_id = models.CharField(
        max_length=255, verbose_name=_("recipient ID"),
    )
    channel = models.CharField(
        max_length=16,
        choices=NotificationChannel.choices,
        verbose_name=_("channel"),
    )
    enabled = models.BooleanField(default=True, verbose_name=_("enabled"))
    alert_severity_min = models.CharField(
        max_length=16,
        blank=True,
        default="info",
        verbose_name=_("minimum alert severity"),
        help_text=_("Only deliver alerts at this severity or higher."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("notification preference")
        verbose_name_plural = _("notification preferences")
        constraints = [
            models.UniqueConstraint(
                fields=["recipient_type", "recipient_id", "channel"],
                name="unique_recipient_channel_preference",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recipient_type}:{self.recipient_id}:{self.channel}"
