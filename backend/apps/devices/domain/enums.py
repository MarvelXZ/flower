from django.db import models
from django.utils.translation import gettext_lazy as _


class DeviceStatus(models.TextChoices):
    PROVISIONING = "provisioning", _("Provisioning")
    ACTIVE = "active", _("Active")
    OFFLINE = "offline", _("Offline")
    RETIRED = "retired", _("Retired")


class ProvisioningStatus(models.TextChoices):
    """Lifecycle stages for device onboarding."""

    UNPROVISIONED = "unprovisioned", _("Unprovisioned")
    IDENTITY_CREATED = "identity_created", _("Identity created")
    CERTIFICATE_ISSUED = "certificate_issued", _("Certificate issued")
    REGISTERED = "registered", _("Registered")
    ACTIVATED = "activated", _("Activated")
    FAILED = "failed", _("Failed")
