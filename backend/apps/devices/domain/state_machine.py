"""Device state machine — transition policies and enforcement.

Every provisioning status transition is validated against a whitelist.
Invalid transitions raise ``DeviceStateTransitionError`` and are logged
for audit purposes.

The state machine is enforced at the service layer — never in the model
— so that business rules are explicit, testable, and auditable.
"""

from apps.devices.domain.enums import ProvisioningStatus


class DeviceStateTransitionError(ValueError):
    """Raised when a provisioning status transition is not allowed."""


# ---------------------------------------------------------------------------
# Allowed transitions
# ---------------------------------------------------------------------------

_PROVISIONING_TRANSITIONS: dict[str, set[str]] = {
    # Fresh registration
    ProvisioningStatus.UNPROVISIONED: {
        ProvisioningStatus.IDENTITY_CREATED,
        ProvisioningStatus.FAILED,
    },
    # Credentials generated, waiting for certificate
    ProvisioningStatus.IDENTITY_CREATED: {
        ProvisioningStatus.CERTIFICATE_ISSUED,
        ProvisioningStatus.REGISTERED,  # skip cert if not using MQTT TLS
        ProvisioningStatus.FAILED,
    },
    # Certificate issued, ready for final registration
    ProvisioningStatus.CERTIFICATE_ISSUED: {
        ProvisioningStatus.REGISTERED,
        ProvisioningStatus.FAILED,
    },
    # Fully provisioned, waiting for activation
    ProvisioningStatus.REGISTERED: {
        ProvisioningStatus.ACTIVATED,
        ProvisioningStatus.FAILED,
    },
    # Active — terminal success state (operational transitions via DeviceStatus)
    ProvisioningStatus.ACTIVATED: {
        ProvisioningStatus.FAILED,  # decommission
    },
    # Failed is terminal — device must be re-provisioned
    ProvisioningStatus.FAILED: set(),
}

# These transitions are NEVER allowed (enforced explicitly):
# - ACTIVATED → UNPROVISIONED (cannot un-provision a live device)
# - ACTIVATED → IDENTITY_CREATED (cannot downgrade)
# - Any → UNPROVISIONED except from UNPROVISIONED itself
# - FAILED → anything (terminal)


def validate_transition(
    *,
    current_status: str,
    target_status: str,
) -> None:
    """Validate a provisioning status transition.

    Raises ``DeviceStateTransitionError`` if the transition is not allowed.
    """
    allowed = _PROVISIONING_TRANSITIONS.get(current_status)
    if allowed is None:
        raise DeviceStateTransitionError(
            f"Unknown provisioning status: '{current_status}'.",
        )

    if target_status not in allowed:
        raise DeviceStateTransitionError(
            f"Cannot transition device provisioning from "
            f"'{current_status}' to '{target_status}'. "
            f"Allowed transitions: {sorted(allowed)}.",
        )


def can_transition(*, current_status: str, target_status: str) -> bool:
    """Return True if the transition is allowed."""
    allowed = _PROVISIONING_TRANSITIONS.get(current_status, set())
    return target_status in allowed


def allowed_transitions(current_status: str) -> set[str]:
    """Return the set of allowed target statuses from the current status."""
    return _PROVISIONING_TRANSITIONS.get(current_status, set())


def is_terminal(status: str) -> bool:
    """Return True if the status has no outgoing transitions."""
    return len(_PROVISIONING_TRANSITIONS.get(status, set())) == 0
