import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.integrations.domain.enums import OutboxStatus


class IntegrationOutbox(models.Model):
    """Tenant-local outbox event created with the canonical owner write."""

    event_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("event ID"),
    )
    idempotency_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name=_("idempotency key"),
    )
    event_type = models.CharField(max_length=120, verbose_name=_("event type"))
    aggregate_type = models.CharField(max_length=120, verbose_name=_("aggregate type"))
    aggregate_id = models.CharField(max_length=120, verbose_name=_("aggregate ID"))
    target_provider_schema = models.CharField(
        max_length=63,
        blank=True,
        verbose_name=_("target provider schema"),
    )
    payload = models.JSONField(default=dict, verbose_name=_("payload"))
    status = models.CharField(
        max_length=32,
        choices=OutboxStatus.choices,
        default=OutboxStatus.PENDING,
        verbose_name=_("status"),
    )
    attempts = models.PositiveIntegerField(default=0, verbose_name=_("attempts"))
    retry_count = models.PositiveIntegerField(default=0, verbose_name=_("retry count"))
    last_error = models.TextField(blank=True, verbose_name=_("last error"))
    available_at = models.DateTimeField(default=timezone.now, verbose_name=_("available at"))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("processed at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("integration outbox")
        verbose_name_plural = _("integration outbox")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["event_id"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["status", "available_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.aggregate_id}"


class OutboxDelivery(models.Model):
    """Delivery attempt for an IntegrationOutbox event."""

    outbox = models.ForeignKey(
        IntegrationOutbox,
        on_delete=models.CASCADE,
        related_name="deliveries",
        verbose_name=_("outbox"),
    )
    attempt_number = models.PositiveIntegerField(default=1, verbose_name=_("attempt number"))
    status = models.CharField(
        max_length=32,
        choices=OutboxStatus.choices,
        default=OutboxStatus.PENDING,
        verbose_name=_("status"),
    )
    error = models.TextField(blank=True, verbose_name=_("error"))
    response_code = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("response code"))
    error_message = models.TextField(blank=True, verbose_name=_("error message"))
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name=_("delivered at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("outbox delivery")
        verbose_name_plural = _("outbox deliveries")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["outbox", "attempt_number"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.outbox_id}:{self.status}"
