from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PlantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.plants"
    verbose_name = _("Plants")

    def ready(self) -> None:
        pass
