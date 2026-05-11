from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.integrations.domain.enums import EngagementStatus


class ProviderEngagement(models.Model):
    """Bilateral agreement between an owner tenant and a provider tenant.

    ``ProviderEngagement`` controls whether the provider tenant is allowed
    to receive synchronised data from the owner and whether the provider's
    inbound API should accept owner requests.

    The engagement lives in the **public/owner** schema (same as
    ``ProviderConnection``) so that the owner is the canonical source of
    truth for the relationship.

    Only an ``active`` engagement allows data sync.  A ``revoked``
    engagement is a terminal state — it cannot transition back to
    ``active``.
    """

    owner_tenant_id = models.CharField(
        max_length=120,
        verbose_name=_("owner tenant ID"),
    )
    provider_tenant_id = models.CharField(
        max_length=120,
        verbose_name=_("provider tenant ID"),
    )
    status = models.CharField(
        max_length=32,
        choices=EngagementStatus.choices,
        default=EngagementStatus.PENDING,
        verbose_name=_("status"),
    )
    scopes = models.JSONField(
        default=list, blank=True, verbose_name=_("scopes"),
        help_text=_("Allowed sync scopes for this engagement."),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    activated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("activated at"),
    )
    suspended_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("suspended at"),
    )
    revoked_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("revoked at"),
    )

    class Meta:
        verbose_name = _("provider engagement")
        verbose_name_plural = _("provider engagements")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_tenant_id", "provider_tenant_id"],
                name="unique_owner_provider_engagement",
            ),
        ]
        indexes = [
            models.Index(fields=["owner_tenant_id", "provider_tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.owner_tenant_id}→{self.provider_tenant_id}:{self.status}"
