import secrets
from datetime import timedelta

from django.db import connection, transaction
from django.utils import timezone

from apps.devices.domain.enums import DeviceStatus, ProvisioningStatus
from apps.devices.domain.state_machine import (
    DeviceStateTransitionError,
    validate_transition,
)
from apps.devices.events import (
    DeviceEvent,
    DeviceEventType,
    emit,
)
from apps.devices.models import Device, DeviceCredential, DeviceHeartbeat
from apps.devices.models.provisioning_audit import record_transition


class DeviceProvisioningError(ValueError):
    """Raised when a device cannot be safely provisioned."""


class DeviceOfflineError(ValueError):
    """Raised when attempting an operation on an offline device."""


def _current_schema_name() -> str:
    return getattr(connection, "schema_name", "")


def _generate_api_key() -> str:
    return f"dk_{secrets.token_urlsafe(32)}"


def _generate_api_secret() -> str:
    return secrets.token_urlsafe(48)


def _transition(
    *,
    device: Device,
    to_status: str,
    triggered_by: str = "",
    metadata: dict | None = None,
) -> None:
    """Validate and record a provisioning status transition."""
    from_status = device.provisioning_status
    validate_transition(current_status=from_status, target_status=to_status)

    device.provisioning_status = to_status
    # The caller must save the device after this.

    record_transition(
        device=device,
        from_status=from_status,
        to_status=to_status,
        triggered_by=triggered_by,
        metadata=metadata,
    )


def _emit_device_event(
    *,
    event_type: str,
    device: Device,
    data: dict | None = None,
) -> None:
    """Emit a canonical device event."""
    emit(DeviceEvent.create(
        event_type=event_type,
        device_serial=device.serial_number,
        device_uuid=str(device.uuid),
        tenant_schema=device.owner_tenant_schema,
        data=data,
    ))


# ---------------------------------------------------------------------------
# Provisioning lifecycle
# ---------------------------------------------------------------------------


def register_device(
    *,
    name: str,
    serial_number: str,
    hardware_revision: str = "",
    firmware_version: str = "",
    owner_tenant_schema: str | None = None,
    capabilities: list[str] | None = None,
    heartbeat_interval_seconds: int = 60,
    mqtt_client_id: str = "",
) -> Device:
    """Register a new device in the owner tenant context.

    The device is created in ``UNPROVISIONED`` provisioning status and
    ``PROVISIONING`` operational status.  It must go through the full
    provisioning pipeline before it can send data.

    Emits: ``device.provisioned``
    """
    schema_name = owner_tenant_schema or _current_schema_name()
    if not schema_name or schema_name == "public":
        raise DeviceProvisioningError("Device registration requires an owner tenant schema.")

    now = timezone.now()

    with transaction.atomic():
        device = Device.objects.create(
            name=name,
            serial_number=serial_number,
            hardware_revision=hardware_revision,
            firmware_version=firmware_version,
            owner_tenant_schema=schema_name,
            status=DeviceStatus.PROVISIONING,
            provisioning_status=ProvisioningStatus.UNPROVISIONED,
            is_active=True,
            capabilities=capabilities or [],
            heartbeat_interval_seconds=heartbeat_interval_seconds,
            mqtt_client_id=mqtt_client_id or f"dev_{serial_number}",
            provisioned_at=now,
        )
        record_transition(
            device=device,
            from_status="",
            to_status=ProvisioningStatus.UNPROVISIONED,
            triggered_by="register_device",
        )
        _emit_device_event(
            event_type=DeviceEventType.PROVISIONED,
            device=device,
        )

    return device


def create_device_credentials(*, device: Device) -> DeviceCredential:
    """Generate API credentials for a device.

    The plaintext API secret is returned once and NEVER stored.
    Only the Argon2 hash is persisted in ``api_secret_hash``.
    The caller is responsible for delivering the secret to the device
    over a secure channel (e.g. during provisioning).

    Enforces state machine: current must allow → IDENTITY_CREATED.

    Emits: ``device.identity_created``
    """
    from argon2 import PasswordHasher

    api_key = _generate_api_key()
    api_secret = _generate_api_secret()
    ph = PasswordHasher()

    with transaction.atomic():
        credential = DeviceCredential.objects.create(
            device=device,
            api_key=api_key,
            api_secret_hash=ph.hash(api_secret),
            is_active=True,
        )

        _transition(
            device=device,
            to_status=ProvisioningStatus.IDENTITY_CREATED,
            triggered_by="create_device_credentials",
        )
        device.save(update_fields=["provisioning_status", "updated_at"])

        _emit_device_event(
            event_type=DeviceEventType.IDENTITY_CREATED,
            device=device,
        )

    # Return the plaintext secret — caller must deliver it securely.
    credential._plaintext_secret = api_secret
    return credential


def complete_provisioning(*, device: Device) -> Device:
    """Mark a device as fully provisioned and ready for activation.

    Enforces state machine: current must allow → REGISTERED.

    Emits: ``device.registered``
    """
    with transaction.atomic():
        _transition(
            device=device,
            to_status=ProvisioningStatus.REGISTERED,
            triggered_by="complete_provisioning",
        )
        device.save(update_fields=["provisioning_status", "updated_at"])

        _emit_device_event(
            event_type=DeviceEventType.REGISTERED,
            device=device,
        )

        return device


def activate_device(*, device: Device) -> Device:
    """Mark a provisioned device as active and ready to send data.

    Enforces state machine: current must allow → ACTIVATED.

    Emits: ``device.activated``
    """
    now = timezone.now()
    with transaction.atomic():
        _transition(
            device=device,
            to_status=ProvisioningStatus.ACTIVATED,
            triggered_by="activate_device",
        )
        device.status = DeviceStatus.ACTIVE
        device.is_active = True
        device.activated_at = now
        device.save(update_fields=[
            "status", "is_active", "provisioning_status",
            "activated_at", "updated_at",
        ])

        _emit_device_event(
            event_type=DeviceEventType.ACTIVATED,
            device=device,
        )

        return device


def deactivate_device(*, device: Device) -> Device:
    """Deactivate a device without deleting its telemetry history.

    Emits: ``device.deactivated``
    """
    device.status = DeviceStatus.RETIRED
    device.is_active = False
    device.save(update_fields=["status", "is_active", "updated_at"])

    _emit_device_event(
        event_type=DeviceEventType.DEACTIVATED,
        device=device,
    )

    return device


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------


def record_heartbeat(
    *,
    device: Device,
    firmware_version: str = "",
    ip_address: str = "",
    rssi: int | None = None,
    battery_level: float | None = None,
) -> DeviceHeartbeat:
    """Record an append-only heartbeat and update device last_seen_at.

    The heartbeat is always appended (never overwritten).  The device's
    ``last_seen_at`` and ``last_ip`` are updated for quick lookups.

    Emits: ``device.heartbeat_received``
    """
    now = timezone.now()
    with transaction.atomic():
        heartbeat = DeviceHeartbeat.objects.create(
            device=device,
            firmware_version=firmware_version,
            ip_address=ip_address,
            rssi=rssi,
            battery_level=battery_level,
        )
        device.last_seen_at = now
        if ip_address:
            device.last_ip = ip_address
        if firmware_version:
            device.firmware_version = firmware_version
        device.save(update_fields=["last_seen_at", "last_ip", "firmware_version", "updated_at"])

        _emit_device_event(
            event_type=DeviceEventType.HEARTBEAT_RECEIVED,
            device=device,
            data={
                "firmware_version": firmware_version,
                "rssi": rssi,
                "battery_level": battery_level,
            },
        )

        return heartbeat


# ---------------------------------------------------------------------------
# Offline detection
# ---------------------------------------------------------------------------


def detect_offline_devices(
    *,
    owner_tenant_schema: str,
    max_missed_heartbeats: int = 3,
) -> list[Device]:
    """Return devices that have missed too many heartbeats.

    A device is considered offline when its most recent heartbeat is older
    than ``heartbeat_interval_seconds * max_missed_heartbeats``.
    """
    now = timezone.now()

    offline_devices = []
    active_devices = Device.objects.filter(
        owner_tenant_schema=owner_tenant_schema,
        status=DeviceStatus.ACTIVE,
    )

    for device in active_devices:
        if device.last_seen_at is None:
            offline_devices.append(device)
            continue
        threshold = device.heartbeat_interval_seconds * max_missed_heartbeats
        if (now - device.last_seen_at).total_seconds() > threshold:
            offline_devices.append(device)

    return offline_devices


def mark_device_offline(*, device: Device) -> Device:
    """Transition an active device to offline status.

    Emits: ``device.offline``
    """
    if device.status != DeviceStatus.ACTIVE:
        raise DeviceOfflineError(
            f"Cannot mark device '{device}' as offline — current status is '{device.status}'.",
        )
    device.status = DeviceStatus.OFFLINE
    device.save(update_fields=["status", "updated_at"])

    _emit_device_event(
        event_type=DeviceEventType.OFFLINE,
        device=device,
    )

    return device


def mark_device_online(*, device: Device) -> Device:
    """Transition an offline device back to active.

    Emits: ``device.online``
    """
    if device.status != DeviceStatus.OFFLINE:
        return device
    device.status = DeviceStatus.ACTIVE
    device.save(update_fields=["status", "updated_at"])

    _emit_device_event(
        event_type=DeviceEventType.ONLINE,
        device=device,
    )

    return device
