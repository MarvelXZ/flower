from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.integrations.domain.enums import ProviderKeyStatus


class ProviderKey(models.Model):
    """HMAC key metadata for an owner-tenant provider connection."""

    provider_connection = models.ForeignKey(
        "integrations.ProviderConnection",
        on_delete=models.CASCADE,
        related_name="provider_keys",
        verbose_name=_("provider connection"),
    )
    key_id = models.CharField(max_length=120, verbose_name=_("key ID"))
    secret_reference = models.CharField(
        max_length=255,
        verbose_name=_("secret reference"),
        help_text=_("Reference to a secret resolver entry; never store the plain secret here."),
    )
    status = models.CharField(
        max_length=32,
        choices=ProviderKeyStatus.choices,
        default=ProviderKeyStatus.ACTIVE,
        verbose_name=_("status"),
    )
    valid_from = models.DateTimeField(verbose_name=_("valid from"))
    valid_until = models.DateTimeField(null=True, blank=True, verbose_name=_("valid until"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    rotated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("rotated at"))
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name=_("revoked at"))

    class Meta:
        verbose_name = _("provider key")
        verbose_name_plural = _("provider keys")
        ordering = ["provider_connection_id", "-created_at"]
        indexes = [
            models.Index(fields=["provider_connection", "status"]),
            models.Index(fields=["key_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider_connection"],
                condition=Q(status=ProviderKeyStatus.ACTIVE),
                name="unique_active_provider_key_per_connection",
            ),
            models.UniqueConstraint(
                fields=["key_id"],
                condition=Q(status=ProviderKeyStatus.ACTIVE),
                name="unique_active_provider_key_id",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.key_id}:{self.status}"
