"""
Audit bounded context.

Responsible for audit trails of manual actions.
Every manual action by a user must be logged here.

CRITICAL: Audit logs are append-only. Never update or delete.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import UUIDModel


class AuditLog(UUIDModel):
    """
    Append-only audit trail of user actions.

    Every create, update, delete, login, and export action
    should create an AuditLog entry. Never update or delete.
    """

    class Action(models.TextChoices):
        CREATE = "create", _("Create")
        UPDATE = "update", _("Update")
        DELETE = "delete", _("Delete")
        LOGIN = "login", _("Login")
        LOGOUT = "logout", _("Logout")
        EXPORT = "export", _("Export")

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
        verbose_name=_("actor"),
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name=_("action"),
    )
    target_type = models.CharField(
        max_length=100,
        verbose_name=_("target type"),
        help_text=_("Model name (e.g., 'devices.Device')."),
    )
    target_id = models.CharField(
        max_length=36,
        verbose_name=_("target ID"),
        help_text=_("UUID of the affected object."),
    )
    changes = models.JSONField(
        default=dict,
        verbose_name=_("changes"),
        help_text=_("Before/after state: {'before': {...}, 'after': {...}}."),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP address"),
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("user agent"),
    )
    occurred_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name=_("occurred at"),
    )

    class Meta:
        verbose_name = _("audit log")
        verbose_name_plural = _("audit logs")
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(fields=["target_type", "target_id"]),
            models.Index(fields=["action", "occurred_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.actor} {self.action} {self.target_type}:{self.target_id}"
