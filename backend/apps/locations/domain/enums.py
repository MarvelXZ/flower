from django.db import models
from django.utils.translation import gettext_lazy as _


class LocationKind(models.TextChoices):
    SITE = "site", _("Site")
    BUILDING = "building", _("Building")
    ROOM = "room", _("Room")
    AREA = "area", _("Area")
    SERVICE_REGION = "service_region", _("Service region")
