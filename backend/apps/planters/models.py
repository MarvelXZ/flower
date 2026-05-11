"""
Planters bounded context.

Responsible for planter (flower pot / container) definitions,
inventory, and status. A planter can have a device installed
and a plant growing in it.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import AuditableModel


class Planter(AuditableModel):
    """
    A physical planter / container that holds a plant and optionally
    has an IoT device installed for monitoring.
    """

    class Material(models.TextChoices):
        PLASTIC = "plastic", _("Plastic")
        CERAMIC = "ceramic", _("Ceramic")
        TERRACOTTA = "terracotta", _("Terracotta")
        METAL = "metal", _("Metal")
        WOOD = "wood", _("Wood")
        FABRIC = "fabric", _("Fabric")

    class Status(models.TextChoices):
        EMPTY = "empty", _("Empty")
        PLANTED = "planted", _("Planted")
        MAINTENANCE = "maintenance", _("Maintenance")

    name = models.CharField(
        max_length=100,
        verbose_name=_("planter name"),
        help_text=_("Human-readable name (e.g., 'Kitchen Window Basil Pot')."),
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("planter code"),
        help_text=_("Unique identifier for inventory tracking."),
    )
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planters",
        verbose_name=_("location"),
    )
    device = models.OneToOneField(
        "devices.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="planter",
        verbose_name=_("installed device"),
        help_text=_("IoT device currently installed in this planter."),
    )
    material = models.CharField(
        max_length=20,
        choices=Material.choices,
        default=Material.PLASTIC,
        verbose_name=_("material"),
    )
    dimensions = models.JSONField(
        default=dict,
        verbose_name=_("dimensions"),
        help_text=_("Physical dimensions: {length_cm, width_cm, depth_cm}."),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EMPTY,
        verbose_name=_("status"),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("active"),
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("notes"),
    )

    class Meta:
        verbose_name = _("planter")
        verbose_name_plural = _("planters")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status", "is_active"]),
            models.Index(fields=["location", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"
