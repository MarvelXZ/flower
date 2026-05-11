from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CareEngineConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.care_engine"
    verbose_name = _("Care engine")
