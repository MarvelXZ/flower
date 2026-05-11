from django.db import models
from django.utils.translation import gettext_lazy as _


class ProviderListingMedia(models.Model):
    """Image or document attached to a provider listing."""

    listing = models.ForeignKey(
        "marketplace.ProviderListing",
        on_delete=models.CASCADE,
        related_name="media",
        verbose_name=_("listing"),
    )
    media_type = models.CharField(
        max_length=16,
        choices=[("image", "Image"), ("document", "Document")],
        verbose_name=_("media type"),
    )
    file_url = models.URLField(max_length=512, verbose_name=_("file URL"))
    sort_order = models.PositiveIntegerField(default=0, verbose_name=_("sort order"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))

    class Meta:
        verbose_name = _("provider listing media")
        verbose_name_plural = _("provider listing media")
        ordering = ["listing", "sort_order"]

    def __str__(self) -> str:
        return f"{self.listing_id}:{self.media_type}"
