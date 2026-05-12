"""Append-only alert event log.

Every alert status change is recorded as an immutable audit entry.
Rows are never modified or deleted — this is the canonical audit log
for alert lifecycle forensics and SLA computation.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class AlertEvent(models.Model):
    """Append-only record of an alert lifecycle event.

    Tracks the full alert lifecycle: created → acknowledged → resolved/dismissed.
    Each event captures the transition (``event_type``) and the actor, if any.
    """

    class EventType(models.TextChoices):
        CREATED = "created", _("Created")
        UPDATED = "updated", _("Updated")
        ACKNOWLEDGED = "acknowledged", _("Acknowledged")
        RESOLVED = "resolved", _("Resolved")
        DISMISSED = "dismissed", _("Dismissed")
        ESCALATED = "escalated", _("Escalated")
        SUPPRESSED = "suppressed", _("Suppressed")

    alert = models.ForeignKey(
        "notifications.Alert",
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("alert"),
    )
    event_type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        verbose_name=_("event type"),
    )
    from_status = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name=_("from status"),
    )
    to_status = models.CharField(
        max_length=32,
        verbose_name=_("to status"),
    )
    triggered_by = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name=_("triggered by"),
        help_text=_("Service, user, or system that triggered this event."),
    )
    metadata = models.JSONField(
        default=dict, blank=True, verbose_name=_("metadata"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        verbose_name = _("alert event")
        verbose_name_plural = _("alert events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["alert", "-created_at"]),
            models.Index(fields=["event_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Alert {self.alert_id}: {self.event_type} ({self.from_status} → {self.to_status})"


def record_alert_event(
    *,
    alert,
    event_type: str,
    from_status: str = "",
    to_status: str = "",
    triggered_by: str = "",
    metadata: dict | None = None,
) -> AlertEvent:
    """Record an alert lifecycle event in the audit trail."""
    return AlertEvent.objects.create(
        alert=alert,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        triggered_by=triggered_by,
        metadata=metadata or {},
    )
