from django.db import models
from django.utils.translation import gettext_lazy as _


class DeviceStatus(models.TextChoices):
    PROVISIONING = "provisioning", _("Provisioning")
    ACTIVE = "active", _("Active")
    OFFLINE = "offline", _("Offline")
    RETIRED = "retired", _("Retired")
