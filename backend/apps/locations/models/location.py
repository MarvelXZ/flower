from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.locations.domain.enums import LocationKind


class Location(models.Model):
    """Physical or service location in a tenant schema."""

    name = models.CharField(max_length=180, verbose_name=_("name"))
    kind = models.CharField(
        max_length=32,
        choices=LocationKind.choices,
        default=LocationKind.SITE,
        verbose_name=_("kind"),
    )
    address = models.CharField(max_length=255, blank=True, verbose_name=_("address"))
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("latitude"),
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_("longitude"),
    )
    timezone = models.CharField(
        max_length=64,
        default="Europe/Belgrade",
        verbose_name=_("timezone"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("location")
        verbose_name_plural = _("locations")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["kind"]),
        ]

    def __str__(self) -> str:
        return self.name
