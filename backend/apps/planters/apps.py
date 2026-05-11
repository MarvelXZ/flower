from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PlantersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.planters"
    verbose_name = _("Planters")

    def ready(self) -> None:
        pass
