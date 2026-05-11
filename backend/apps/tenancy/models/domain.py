from django.utils.translation import gettext_lazy as _
from django_tenants.models import DomainMixin


class Domain(DomainMixin):
    """Domain mapping used by django-tenants."""

    class Meta:
        verbose_name = _("domain")
        verbose_name_plural = _("domains")
        ordering = ["domain"]

    def __str__(self) -> str:
        return self.domain
