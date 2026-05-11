from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.audit.domain.enums import AuditAction


class AuditLog(models.Model):
    """Append-only audit record for tenant actions."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("actor"),
    )
    action = models.CharField(max_length=32, choices=AuditAction.choices, verbose_name=_("action"))
    target_type = models.CharField(max_length=120, verbose_name=_("target type"))
    target_id = models.CharField(max_length=120, verbose_name=_("target ID"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("metadata"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action}:{self.target_type}:{self.target_id}"
