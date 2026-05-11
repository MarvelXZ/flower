from django.db import models
from django.utils.translation import gettext_lazy as _


class PlantSpecies(models.Model):
    """Catalog species used by owner plants and care profiles."""

    name = models.CharField(max_length=160, verbose_name=_("name"))
    slug = models.SlugField(max_length=180, unique=True, verbose_name=_("slug"))
    description = models.TextField(blank=True, verbose_name=_("description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("plant species")
        verbose_name_plural = _("plant species")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
