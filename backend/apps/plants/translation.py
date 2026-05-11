"""
Model translation configuration for the plants bounded context.

This module registers translatable fields with django-modeltranslation.
All user-facing text fields should be listed here.
"""

from modeltranslation.translator import TranslationOptions, register

from apps.plants.models import PlantType


@register(PlantType)
class PlantTypeTranslationOptions(TranslationOptions):
    fields = ("name", "description")
