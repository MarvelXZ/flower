from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TelemetryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telemetry"
    verbose_name = _("Telemetry")

    def ready(self) -> None:
        pass
