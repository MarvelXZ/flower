from django.db import models
from django.utils.translation import gettext_lazy as _


class EmailDestination(models.Model):
    """Registered email destination for a tenant or user."""

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="email_destinations",
        verbose_name=_("user"),
    )
    tenant_id = models.CharField(
        max_length=120, verbose_name=_("tenant ID"),
    )
    email = models.EmailField(max_length=254, verbose_name=_("email"))
    is_verified = models.BooleanField(default=False, verbose_name=_("verified"))
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("email destination")
        verbose_name_plural = _("email destinations")
        ordering = ["email"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "email"],
                name="unique_tenant_email_destination",
            ),
        ]

    def __str__(self) -> str:
        return self.email
