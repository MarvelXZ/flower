"""
Notifications bounded context.

Responsible for notification channels, templates, and delivery logs.
Supports email, SMS, push, and in-app notifications.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class NotificationLog(UUIDModel):
    """
    Log of a notification sent to a user.

    Tracks delivery status and supports multiple channels.
    """

    class Channel(models.TextChoices):
        EMAIL = "email", _("Email")
        SMS = "sms", _("SMS")
        PUSH = "push", _("Push")
        IN_APP = "in_app", _("In-App")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENT = "sent", _("Sent")
        DELIVERED = "delivered", _("Delivered")
        FAILED = "failed", _("Failed")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("recipient"),
    )
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        verbose_name=_("channel"),
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("subject"),
    )
    body = models.TextField(
        verbose_name=_("body"),
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("status"),
        db_index=True,
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("sent at"),
    )
    error_message = models.TextField(
        blank=True,
        verbose_name=_("error message"),
    )
    related_object_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("related object type"),
        help_text=_("Model name of the related object (e.g., 'alerts.Alert')."),
    )
    related_object_id = models.CharField(
        max_length=36,
        blank=True,
        verbose_name=_("related object ID"),
    )

    class Meta:
        verbose_name = _("notification log")
        verbose_name_plural = _("notification logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "status"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["related_object_type", "related_object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel} → {self.recipient}: {self.subject or self.body[:50]}"
