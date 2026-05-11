from django.db import models
from django.utils.translation import gettext_lazy as _


class MobileSession(models.Model):
    """Provider/mobile app session backed by JWT refresh token."""

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="mobile_sessions",
        verbose_name=_("user"),
    )
    tenant_schema = models.CharField(
        max_length=120, verbose_name=_("tenant schema"),
    )
    device_id = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("device ID"),
    )
    platform = models.CharField(
        max_length=16,
        choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")],
        default="web",
        verbose_name=_("platform"),
    )
    app_version = models.CharField(
        max_length=32, null=True, blank=True, verbose_name=_("app version"),
    )
    refresh_token_jti = models.CharField(
        max_length=255, verbose_name=_("refresh token JTI"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    last_seen_at = models.DateTimeField(auto_now=True, verbose_name=_("last seen at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    revoked_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("revoked at"),
    )

    class Meta:
        verbose_name = _("mobile session")
        verbose_name_plural = _("mobile sessions")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["refresh_token_jti"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.platform}"
