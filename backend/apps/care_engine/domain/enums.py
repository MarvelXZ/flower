from django.db import models
from django.utils.translation import gettext_lazy as _


class CareKnowledgeStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    ARCHIVED = "archived", _("Archived")
