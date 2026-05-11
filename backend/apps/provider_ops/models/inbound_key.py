from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.provider_ops.domain.enums import InboundKeyStatus


class ProviderInboundKey(models.Model):
    """Inbound HMAC key for a provider tenant to authenticate owner requests.

    This model lives in the provider tenant schema. Each key binds a
    ``key_id`` to a specific ``source_owner_tenant_id``, so the provider
    inbound B2B API can verify that an owner request is authorised for
    this provider tenant.

    The plain shared secret is never stored here — only a reference
    (``secret_reference``) that a secret resolver can look up.
    """

    key_id = models.CharField(
        max_length=120,
        unique=True,
        verbose_name=_("key ID"),
        help_text=_("Public identifier sent in the X-B2B-Key-Id header."),
    )
    source_owner_tenant_id = models.CharField(
        max_length=120,
        verbose_name=_("source owner tenant ID"),
        help_text=_("The owner tenant that this key authenticates requests from."),
    )
    secret_reference = models.CharField(
        max_length=255,
        verbose_name=_("secret reference"),
        help_text=_("Reference to a secret resolver entry; never store the plain secret here."),
    )
    status = models.CharField(
        max_length=32,
        choices=InboundKeyStatus.choices,
        default=InboundKeyStatus.ACTIVE,
        verbose_name=_("status"),
    )
    valid_from = models.DateTimeField(verbose_name=_("valid from"))
    valid_until = models.DateTimeField(
        null=True, blank=True, verbose_name=_("valid until"),
    )
    scopes = models.JSONField(
        default=list, blank=True, verbose_name=_("scopes"),
        help_text=_("Allowed endpoint scopes for this key (e.g. telemetry:write)."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    revoked_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("revoked at"),
    )

    class Meta:
        verbose_name = _("provider inbound key")
        verbose_name_plural = _("provider inbound keys")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["key_id", "status"]),
            models.Index(fields=["source_owner_tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.key_id}:{self.status}"
