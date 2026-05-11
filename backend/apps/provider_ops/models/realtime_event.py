"""Event store for realtime reconnect/resume and delta fallback."""

from django.db import models
from django.utils.translation import gettext_lazy as _


class RealtimeEvent(models.Model):
    """Persisted event for WebSocket replay and delta fallback.

    Created alongside every state change in tasks, SLA, and notifications.
    Used by mobile clients to catch up after disconnect.
    """

    tenant_schema = models.CharField(
        max_length=120, verbose_name=_("tenant schema"),
    )
    event_type = models.CharField(
        max_length=64, verbose_name=_("event type"),
    )
    entity_type = models.CharField(
        max_length=64, verbose_name=_("entity type"),
    )
    entity_id = models.CharField(
        max_length=255, verbose_name=_("entity ID"),
    )
    version = models.PositiveIntegerField(default=1, verbose_name=_("version"))
    payload = models.JSONField(default=dict, blank=True, verbose_name=_("payload"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("realtime event")
        verbose_name_plural = _("realtime events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_schema", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}:{self.entity_id}"
