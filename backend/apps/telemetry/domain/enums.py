from django.db import models
from django.utils.translation import gettext_lazy as _


class ReadingSource(models.TextChoices):
    MQTT = "mqtt", _("MQTT")
    API = "api", _("API")
    IMPORT = "import", _("Import")
