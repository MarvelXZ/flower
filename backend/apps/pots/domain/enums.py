from django.db import models
from django.utils.translation import gettext_lazy as _


class PotStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    IN_STORAGE = "in_storage", _("In storage")
    RETIRED = "retired", _("Retired")
