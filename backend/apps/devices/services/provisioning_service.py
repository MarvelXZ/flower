from django.db import transaction
from django.db import connection
from django.utils import timezone

from apps.devices.domain.enums import DeviceStatus
from apps.devices.models import Device


class DeviceProvisioningError(ValueError):
    """Raised when a device cannot be safely provisioned."""


def _current_schema_name() -> str:
    return getattr(connection, "schema_name", "")


def register_device(
    *,
    name: str,
    owner_tenant_schema: str | None = None,
    status: str = DeviceStatus.PROVISIONING,
) -> Device:
    """Register a device in the owner tenant context."""
    schema_name = owner_tenant_schema or _current_schema_name()
    if not schema_name or schema_name == "public":
        raise DeviceProvisioningError("Device registration requires an owner tenant schema.")

    now = timezone.now()

    with transaction.atomic():
        return Device.objects.create(
            name=name,
            owner_tenant_schema=schema_name,
            status=status,
            is_active=True,
            provisioned_at=now,
        )


def activate_device(*, device: Device) -> Device:
    """Mark a provisioned device as active."""
    now = timezone.now()
    device.status = DeviceStatus.ACTIVE
    device.is_active = True
    device.activated_at = now
    device.save(update_fields=["status", "is_active", "activated_at", "updated_at"])
    return device


def deactivate_device(*, device: Device) -> Device:
    """Deactivate a device without deleting its telemetry history."""
    device.status = DeviceStatus.RETIRED
    device.is_active = False
    device.save(update_fields=["status", "is_active", "updated_at"])
    return device
