from django.db import models
from django.utils.translation import gettext_lazy as _


class PlantStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    NEEDS_ATTENTION = "needs_attention", _("Needs attention")
    REMOVED = "removed", _("Removed")
