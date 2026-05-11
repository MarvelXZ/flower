from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.plants.domain.enums import PlantStatus


class Plant(models.Model):
    """A concrete plant instance in an owner tenant schema."""

    name = models.CharField(max_length=160, verbose_name=_("name"))
    species = models.ForeignKey(
        "care_engine.PlantSpecies",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plants",
        verbose_name=_("species"),
    )
    status = models.CharField(
        max_length=32,
        choices=PlantStatus.choices,
        default=PlantStatus.ACTIVE,
        verbose_name=_("status"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("plant")
        verbose_name_plural = _("plants")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
