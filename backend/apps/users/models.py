"""
Users bounded context.

Responsible for users, roles, permissions, and authentication
within a single tenant.
"""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model with UUID primary key and role-based access.

    This replaces Django's default User. Must be configured via
    AUTH_USER_MODEL before the first migration.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_("ID"),
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ("admin", _("Administrator")),
            ("gardener", _("Gardener")),
            ("expert", _("Expert")),
        ],
        default="gardener",
        verbose_name=_("role"),
        help_text=_("User role within the tenant organization."),
    )
    language = models.CharField(
        max_length=5,
        choices=[
            ("sr", "Srpski"),
            ("en", "English"),
            ("hr", "Hrvatski"),
            ("sl", "Slovenščina"),
            ("mk", "Македонски"),
            ("sq", "Shqip"),
            ("el", "Ελληνικά"),
            ("de", "Deutsch"),
        ],
        default="sr",
        verbose_name=_("language"),
        help_text=_("Preferred interface language."),
    )
    phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name=_("phone"),
        help_text=_("Contact phone number."),
    )
    timezone = models.CharField(
        max_length=50,
        default="Europe/Belgrade",
        verbose_name=_("timezone"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("updated at"),
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["username"]

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
