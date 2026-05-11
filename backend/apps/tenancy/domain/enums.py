from django.db import models
from django.utils.translation import gettext_lazy as _


class TenantKind(models.TextChoices):
    OWNER = "owner", _("Owner")
    PROVIDER = "provider", _("Provider")
    HYBRID = "hybrid", _("Hybrid")
    MARKETPLACE_ADMIN = "marketplace_admin", _("Marketplace admin")
