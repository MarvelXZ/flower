"""
Locations bounded context.

Responsible for physical locations (sites, greenhouses, indoor areas)
where planters and devices are installed.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditableModel


class Location(AuditableModel):
    """
    A physical location where planters and devices are installed.

    Examples: greenhouse, apartment balcony, office, garden.
    """

    class LocationType(models.TextChoices):
        GREENHOUSE = "greenhouse", _("Greenhouse")
        INDOOR = "indoor", _("Indoor")
        OUTDOOR = "outdoor", _("Outdoor")
        BALCONY = "balcony", _("Balcony")
        OFFICE = "office", _("Office")
        LABORATORY = "laboratory", _("Laboratory")

    name = models.CharField(
        max_length=100,
        verbose_name=_("location name"),
        help_text=_("Human-readable name (e.g., 'Main Greenhouse')."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("address"),
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("latitude"),
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("longitude"),
    )
    timezone = models.CharField(
        max_length=50,
        default="Europe/Belgrade",
        verbose_name=_("timezone"),
    )
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.INDOOR,
        verbose_name=_("location type"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    class Meta:
        verbose_name = _("location")
        verbose_name_plural = _("locations")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["location_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name
