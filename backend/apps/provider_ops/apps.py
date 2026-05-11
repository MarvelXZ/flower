from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProviderOpsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.provider_ops"
    verbose_name = _("Provider operations")
