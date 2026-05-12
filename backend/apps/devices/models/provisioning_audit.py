"""Append-only provisioning audit trail.

Every provisioning state change is recorded as an immutable audit entry.
Rows are never modified or deleted — this is the canonical audit log for
device lifecycle forensics, SLA computation, and compliance.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ProvisioningAuditEntry(models.Model):
    """Append-only record of a provisioning state change.

    Each entry captures the full transition (``from_status`` →
    ``to_status``), who or what triggered it, and any relevant metadata.
    """

    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="provisioning_audit",
        verbose_name=_("device"),
    )
    from_status = models.CharField(
        max_length=32,
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
        help_text=_("Service, user, or system that triggered this transition."),
    )
    metadata = models.JSONField(
        default=dict, blank=True, verbose_name=_("metadata"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("created at"),
    )

    class Meta:
        verbose_name = _("provisioning audit entry")
        verbose_name_plural = _("provisioning audit entries")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.device_id}: {self.from_status} → {self.to_status}"


def record_transition(
    *,
    device,
    from_status: str,
    to_status: str,
    triggered_by: str = "",
    metadata: dict | None = None,
) -> ProvisioningAuditEntry:
    """Record a provisioning state transition in the audit trail.

    This is called by every provisioning service function that changes
    the device's ``provisioning_status``.  The audit entry is created
    in the same database transaction.
    """
    return ProvisioningAuditEntry.objects.create(
        device=device,
        from_status=from_status,
        to_status=to_status,
        triggered_by=triggered_by,
        metadata=metadata or {},
    )
