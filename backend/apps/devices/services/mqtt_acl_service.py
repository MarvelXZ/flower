"""Tenant-aware MQTT ACL service.

Validates that MQTT publish/subscribe operations stay within the
device's tenant boundary.  This is the policy enforcement layer that
prevents cross-tenant MQTT access.

Topic structure::

    tenant/{tenant_schema}/device/{device_serial}/telemetry
    tenant/{tenant_schema}/device/{device_serial}/heartbeat
    tenant/{tenant_schema}/device/{device_serial}/shadow
    tenant/{tenant_schema}/device/{device_serial}/ota/status
    tenant/{tenant_schema}/provider/{provider_schema}/cmd
"""

from dataclasses import dataclass


class MqttAclError(ValueError):
    """Raised when an MQTT operation violates the ACL policy."""


class TenantIsolationError(MqttAclError):
    """Raised when a client attempts to access another tenant's topics."""


class DeviceSpoofingError(MqttAclError):
    """Raised when a client_id does not match the topic device."""


@dataclass(frozen=True)
class MqttTopic:
    """Parsed MQTT topic with tenant, device, and action components."""

    tenant_schema: str
    device_serial: str
    action: str  # telemetry, heartbeat, shadow, ota/status
    raw: str

    @classmethod
    def parse(cls, topic: str) -> "MqttTopic | None":
        """Parse a tenant-scoped MQTT topic.

        Returns ``None`` if the topic does not match the expected structure.
        """
        parts = topic.strip("/").split("/")
        if len(parts) < 5:
            return None
        if parts[0] != "tenant":
            return None
        return cls(
            tenant_schema=parts[1],
            device_serial=parts[3],
            action="/".join(parts[4:]),
            raw=topic,
        )


# Allowed publish topics per device role.
ALLOWED_DEVICE_PUBLISH_ACTIONS = {
    "telemetry",
    "heartbeat",
    "shadow/reported",
    "ota/status",
}

# Allowed subscribe topics per device role.
ALLOWED_DEVICE_SUBSCRIBE_ACTIONS = {
    "shadow/desired",
    "ota/update",
    "cmd",
}


def validate_device_publish(
    *,
    topic: str,
    client_id: str,
    tenant_schema: str,
) -> None:
    """Validate that a device is allowed to publish to the given topic.

    Rules:
    - The topic must be in the device's own tenant.
    - The topic's ``device_serial`` segment must match the MQTT client_id.
    - Only whitelisted action types are allowed.
    """
    parsed = MqttTopic.parse(topic)
    if parsed is None:
        raise MqttAclError(f"Invalid topic structure: {topic}")

    if parsed.tenant_schema != tenant_schema:
        raise TenantIsolationError(
            f"Device '{client_id}' (tenant={tenant_schema}) cannot publish "
            f"to topic in tenant '{parsed.tenant_schema}'.",
        )

    if parsed.device_serial != client_id:
        raise DeviceSpoofingError(
            f"MQTT client_id '{client_id}' does not match topic device "
            f"'{parsed.device_serial}'.",
        )

    if parsed.action not in ALLOWED_DEVICE_PUBLISH_ACTIONS:
        raise MqttAclError(
            f"Device '{client_id}' is not allowed to publish to "
            f"action '{parsed.action}'.",
        )


def validate_device_subscribe(
    *,
    topic: str,
    client_id: str,
    tenant_schema: str,
) -> None:
    """Validate that a device is allowed to subscribe to the given topic.

    Rules:
    - Same tenant and device checks as publish.
    - Only whitelisted subscribe actions are allowed (shadow/desired, ota/update, cmd).
    """
    parsed = MqttTopic.parse(topic)
    if parsed is None:
        raise MqttAclError(f"Invalid topic structure: {topic}")

    if parsed.tenant_schema != tenant_schema:
        raise TenantIsolationError(
            f"Device '{client_id}' (tenant={tenant_schema}) cannot subscribe "
            f"to topic in tenant '{parsed.tenant_schema}'.",
        )

    if parsed.device_serial != client_id:
        raise DeviceSpoofingError(
            f"MQTT client_id '{client_id}' does not match topic device "
            f"'{parsed.device_serial}'.",
        )

    if parsed.action not in ALLOWED_DEVICE_SUBSCRIBE_ACTIONS:
        raise MqttAclError(
            f"Device '{client_id}' is not allowed to subscribe to "
            f"action '{parsed.action}'.",
        )


def build_device_topic(
    *,
    tenant_schema: str,
    device_serial: str,
    action: str,
) -> str:
    """Build a canonical MQTT topic for a device."""
    return f"tenant/{tenant_schema}/device/{device_serial}/{action}"


def build_provider_topic(
    *,
    tenant_schema: str,
    provider_schema: str,
    action: str,
) -> str:
    """Build a canonical MQTT topic for a provider."""
    return f"tenant/{tenant_schema}/provider/{provider_schema}/{action}"
