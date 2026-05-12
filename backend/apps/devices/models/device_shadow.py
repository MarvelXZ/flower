"""Device shadow service — desired vs reported state synchronisation.

The device shadow pattern keeps two copies of device state:

- **Reported** — what the device says its state is (device → cloud).
- **Desired** — what the cloud wants the device state to be (cloud → device).

The delta between them drives OTA updates, configuration changes, and
command delivery.  This service manages the cloud-side shadow storage.
"""

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class DeviceShadow(models.Model):
    """Cloud-side device shadow storing desired and reported state.

    Each device has exactly one shadow row.  The ``reported`` and
    ``desired`` JSON fields are compared to compute the delta that
    drives downstream actions (OTA, config push, commands).
    """

    device = models.OneToOneField(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="shadow",
        verbose_name=_("device"),
    )
    reported = models.JSONField(
        default=dict, blank=True, verbose_name=_("reported state"),
        help_text=_("Last state reported by the device."),
    )
    desired = models.JSONField(
        default=dict, blank=True, verbose_name=_("desired state"),
        help_text=_("State the cloud wants the device to converge to."),
    )
    reported_version = models.PositiveIntegerField(
        default=0, verbose_name=_("reported version"),
    )
    desired_version = models.PositiveIntegerField(
        default=0, verbose_name=_("desired version"),
    )
    last_reported_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("last reported at"),
    )
    last_desired_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("last desired at"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("updated at"))

    class Meta:
        verbose_name = _("device shadow")
        verbose_name_plural = _("device shadows")

    def __str__(self) -> str:
        return f"Shadow for device {self.device_id}"


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

class ShadowError(ValueError):
    """Base error for shadow operations."""


class ShadowVersionConflict(ShadowError):
    """Raised when a reported update has a version <= the current version."""


def get_or_create_shadow(*, device) -> DeviceShadow:
    """Return the shadow for a device, creating it if necessary."""
    shadow, _created = DeviceShadow.objects.get_or_create(device=device)
    return shadow


def update_reported_state(
    *,
    device,
    reported: dict,
    version: int | None = None,
) -> DeviceShadow:
    """Update the reported state from a device.

    If ``version`` is provided, it must be greater than the current
    ``reported_version`` (optimistic concurrency).
    """
    now = timezone.now()
    with transaction.atomic():
        shadow, _ = DeviceShadow.objects.select_for_update().get_or_create(
            device=device,
        )

        if version is not None and version <= shadow.reported_version:
            raise ShadowVersionConflict(
                f"Reported version {version} <= current {shadow.reported_version} "
                f"for device {device}.",
            )

        shadow.reported = reported
        shadow.reported_version = version or (shadow.reported_version + 1)
        shadow.last_reported_at = now
        shadow.save(update_fields=[
            "reported", "reported_version", "last_reported_at", "updated_at",
        ])
        return shadow


def update_desired_state(
    *,
    device,
    desired: dict,
) -> DeviceShadow:
    """Update the desired state that the cloud wants the device to converge to.

    Increments ``desired_version`` to signal the device that a new desired
    state is available.
    """
    now = timezone.now()
    with transaction.atomic():
        shadow, _ = DeviceShadow.objects.select_for_update().get_or_create(
            device=device,
        )
        shadow.desired = desired
        shadow.desired_version += 1
        shadow.last_desired_at = now
        shadow.save(update_fields=[
            "desired", "desired_version", "last_desired_at", "updated_at",
        ])
        return shadow


def compute_shadow_delta(*, shadow: DeviceShadow) -> dict:
    """Compute the delta between desired and reported state.

    Returns a dict of keys present in ``desired`` that differ from
    ``reported``.  This delta drives OTA updates and config pushes.
    """
    delta = {}
    for key, desired_value in shadow.desired.items():
        reported_value = shadow.reported.get(key)
        if reported_value != desired_value:
            delta[key] = {
                "desired": desired_value,
                "reported": reported_value,
            }
    return delta


def has_pending_desired(*, shadow: DeviceShadow) -> bool:
    """Return True if the device has not yet converged to the desired state."""
    return shadow.desired_version > shadow.reported_version
