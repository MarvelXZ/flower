from django.db import models
from django.utils.translation import gettext_lazy as _


class RuleCode(models.TextChoices):
    SOIL_MOISTURE_LOW = "soil_moisture_low", _("Soil moisture low")
    SOIL_MOISTURE_HIGH = "soil_moisture_high", _("Soil moisture high")
    TEMPERATURE_LOW = "temperature_low", _("Temperature low")
    TEMPERATURE_HIGH = "temperature_high", _("Temperature high")
    AIR_HUMIDITY_LOW = "air_humidity_low", _("Air humidity low")
    AIR_HUMIDITY_HIGH = "air_humidity_high", _("Air humidity high")
    BATTERY_LOW = "battery_low", _("Battery low")
    DEVICE_OFFLINE = "device_offline", _("Device offline")
