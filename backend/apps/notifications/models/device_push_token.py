from django.db import models
from django.utils.translation import gettext_lazy as _


class DevicePushToken(models.Model):
    """Registered push notification token for a device."""

    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="push_tokens",
        verbose_name=_("user"),
    )
    tenant_id = models.CharField(
        max_length=120, verbose_name=_("tenant ID"),
    )
    provider_type = models.CharField(
        max_length=8,
        choices=[("fcm", "FCM"), ("apns", "APNs")],
        verbose_name=_("provider type"),
    )
    token = models.CharField(
        max_length=512, unique=True, verbose_name=_("token"),
    )
    platform = models.CharField(
        max_length=16,
        choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web")],
        default="android",
        verbose_name=_("platform"),
    )
    app_version = models.CharField(
        max_length=32, null=True, blank=True, verbose_name=_("app version"),
    )
    device_name = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_("device name"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("active"))
    last_seen_at = models.DateTimeField(auto_now=True, verbose_name=_("last seen at"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("device push token")
        verbose_name_plural = _("device push tokens")
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["tenant_id", "is_active"]),
            models.Index(fields=["provider_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider_type}:{self.platform}:{self.token[:16]}"
