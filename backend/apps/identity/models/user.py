import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.identity.domain.enums import UserRole


class User(AbstractUser):
    """Tenant-scoped user model."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )
    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.MEMBER,
        verbose_name=_("role"),
    )
    language = models.CharField(max_length=8, default="sr", verbose_name=_("language"))
    timezone = models.CharField(
        max_length=64,
        default="Europe/Belgrade",
        verbose_name=_("timezone"),
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username
