from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.integrations.domain.enums import ProviderConnectionStatus


class ProviderConnection(models.Model):
    """Owner-tenant connection metadata for outbound provider B2B delivery."""

    provider_tenant_id = models.CharField(max_length=120, verbose_name=_("provider tenant ID"))
    provider_base_url = models.URLField(verbose_name=_("provider base URL"))
    api_key_hash = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("API key hash"),
        help_text=_("Placeholder for encrypted/hashed provider API credential reference."),
    )
    key_id = models.CharField(
        max_length=120,
        blank=True,
        verbose_name=_("key ID"),
        help_text=_("Public identifier for HMAC signing key selection."),
    )
    shared_secret_reference = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("shared secret reference"),
        help_text=_("Development placeholder; replace with encrypted secret manager reference."),
    )
    status = models.CharField(
        max_length=32,
        choices=ProviderConnectionStatus.choices,
        default=ProviderConnectionStatus.ACTIVE,
        verbose_name=_("status"),
    )
    scopes = models.JSONField(default=list, blank=True, verbose_name=_("scopes"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name=_("revoked at"))

    class Meta:
        verbose_name = _("provider connection")
        verbose_name_plural = _("provider connections")
        ordering = ["provider_tenant_id"]
        indexes = [
            models.Index(fields=["provider_tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider_tenant_id}:{self.status}"
