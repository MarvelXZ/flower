"""
Plants bounded context.

Responsible for plant species, care profiles, and plant instances
assigned to planters and locations.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditableModel, UUIDModel


class PlantType(AuditableModel):
    """
    A plant species or variety with care requirements.

    The care_profile JSON field stores structured care parameters
    that automation rules can reference.
    """

    class LightRequirement(models.TextChoices):
        FULL_SUN = "full_sun", _("Full Sun")
        PARTIAL_SUN = "partial_sun", _("Partial Sun")
        SHADE = "shade", _("Shade")
        DEEP_SHADE = "deep_shade", _("Deep Shade")

    class WaterFrequency(models.TextChoices):
        DAILY = "daily", _("Daily")
        EVERY_2_DAYS = "every_2_days", _("Every 2 Days")
        TWICE_WEEKLY = "twice_weekly", _("Twice Weekly")
        WEEKLY = "weekly", _("Weekly")
        BIWEEKLY = "biweekly", _("Biweekly")

    key = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("plant type key"),
        help_text=_("Machine-readable identifier (e.g., 'tomato', 'basil')."),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("name"),
        help_text=_("Common name of the plant species."),
    )
    scientific_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name=_("scientific name"),
        help_text=_("Binomial nomenclature (e.g., 'Solanum lycopersicum')."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
    )
    light_requirement = models.CharField(
        max_length=20,
        choices=LightRequirement.choices,
        default=LightRequirement.PARTIAL_SUN,
        verbose_name=_("light requirement"),
    )
    water_frequency = models.CharField(
        max_length=20,
        choices=WaterFrequency.choices,
        default=WaterFrequency.TWICE_WEEKLY,
        verbose_name=_("watering frequency"),
    )
    min_temperature_c = models.FloatField(
        default=10.0,
        verbose_name=_("minimum temperature (°C)"),
    )
    max_temperature_c = models.FloatField(
        default=35.0,
        verbose_name=_("maximum temperature (°C)"),
    )
    min_humidity = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("minimum humidity (%)"),
    )
    max_humidity = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_("maximum humidity (%)"),
    )
    care_profile = models.JSONField(
        default=dict,
        verbose_name=_("care profile"),
        help_text=_(
            "Structured care parameters for automation. "
            "Example: {'soil_moisture_min': 30, 'light_min_lux': 5000}"
        ),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    class Meta:
        verbose_name = _("plant type")
        verbose_name_plural = _("plant types")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return self.name


class Plant(AuditableModel):
    """
    An actual plant instance in the system.

    Represents a physical plant assigned to a planter
    and tracked by the IoT system.
    """

    class Status(models.TextChoices):
        HEALTHY = "healthy", _("Healthy")
        ATTENTION = "attention", _("Needs Attention")
        CRITICAL = "critical", _("Critical")
        DORMANT = "dormant", _("Dormant")
        REMOVED = "removed", _("Removed")

    name = models.CharField(
        max_length=100,
        verbose_name=_("plant name"),
        help_text=_("Human-readable name (e.g., 'Kitchen Basil')."),
    )
    plant_type = models.ForeignKey(
        PlantType,
        on_delete=models.PROTECT,
        related_name="plants",
        verbose_name=_("plant type"),
    )
    planter = models.ForeignKey(
        "planters.Planter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plants",
        verbose_name=_("planter"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.HEALTHY,
        verbose_name=_("status"),
    )
    planted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("planted at"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("notes"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )

    class Meta:
        verbose_name = _("plant")
        verbose_name_plural = _("plants")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["plant_type", "is_active"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.plant_type.name})"


class PlantLocation(UUIDModel):
    """
    Tracks where a plant is placed within a location.

    Allows moving plants between locations/planters
    with a full history of placements.
    """

    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name="placements",
        verbose_name=_("plant"),
    )
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.CASCADE,
        related_name="plant_placements",
        verbose_name=_("location"),
    )
    position = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_("position"),
        help_text=_("Position within the location (e.g., 'A3', 'window-sill')."),
    )
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("assigned at"),
    )
    removed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("removed at"),
    )

    class Meta:
        verbose_name = _("plant location")
        verbose_name_plural = _("plant locations")
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["plant", "removed_at"]),
            models.Index(fields=["location", "removed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.plant.name} @ {self.location.name}"
