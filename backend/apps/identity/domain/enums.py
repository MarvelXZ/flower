from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    ADMIN = "admin", _("Administrator")
    OWNER_MANAGER = "owner_manager", _("Owner manager")
    PROVIDER_OPERATOR = "provider_operator", _("Provider operator")
    MEMBER = "member", _("Member")
