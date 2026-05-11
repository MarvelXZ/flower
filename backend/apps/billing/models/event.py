from django.db import models
from django.utils.translation import gettext_lazy as _


class BillingEvent(models.Model):
    """Audit log entry for billing and subscription events."""

    tenant_id = models.CharField(max_length=120, verbose_name=_("tenant ID"))
    event_type = models.CharField(max_length=64, verbose_name=_("event type"))
    external_event_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("external event ID"),
    )
    payload = models.JSONField(default=dict, blank=True, verbose_name=_("payload"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("billing event")
        verbose_name_plural = _("billing events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "event_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.tenant_id}:{self.event_type}"
