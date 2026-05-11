from modeltranslation.translator import TranslationOptions, register

from apps.care_engine.models import PlantSpecies


@register(PlantSpecies)
class PlantSpeciesTranslationOptions(TranslationOptions):
    fields = ("name", "description")
