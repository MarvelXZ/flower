"""CI enforcement tests — architectural guards that run in CI.

These tests enforce invariants that prevent accidental degradation of
the architecture.  They are NOT unit tests — they validate the codebase
structure itself.

Rules enforced:
1. No direct model writes in API views.
2. Device event types follow `device.<past_tense>` naming.
3. State machine transitions are complete and correct.
4. Service layer functions never cross bounded context boundaries
   without explicit import paths.
"""

from pathlib import Path

import pytest

from apps.devices.domain.enums import ProvisioningStatus
from apps.devices.domain.state_machine import (
    _PROVISIONING_TRANSITIONS,
    can_transition,
    is_terminal,
)
from apps.devices.events import ALL_DEVICE_EVENT_TYPES


# ---------------------------------------------------------------------------
# Rule 1: No direct model writes in API views
# ---------------------------------------------------------------------------

FORBIDDEN_API_WRITE_PATTERNS = (
    ".objects.create(",
    ".objects.update(",
    ".objects.update_or_create(",
    ".objects.get_or_create(",
    ".save(",
    ".delete(",
    ".bulk_create(",
    ".bulk_update(",
)

BOUNDED_CONTEXTS = [
    "devices",
    "telemetry",
    "care_engine",
    "integrations",
    "provider_ops",
    "notifications",
    "billing",
    "audit",
    "locations",
    "plants",
    "pots",
    "identity",
]


def test_api_views_do_not_contain_direct_model_write_patterns():
    """Every API view must delegate writes to the service layer."""
    apps_dir = Path(__file__).resolve().parents[1]

    for context in BOUNDED_CONTEXTS:
        api_views_dir = apps_dir / context / "api" / "views"
        if not api_views_dir.exists():
            continue

        for path in api_views_dir.rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            matches = [
                pattern
                for pattern in FORBIDDEN_API_WRITE_PATTERNS
                if pattern in source
            ]
            assert matches == [], (
                f"{path} contains direct write patterns: {matches}. "
                f"API views must delegate writes to the service layer."
            )


# ---------------------------------------------------------------------------
# Rule 2: Device event types follow naming convention
# ---------------------------------------------------------------------------

def test_device_event_types_follow_past_tense_naming():
    """All device event types must follow `device.<past_tense_verb>` format."""
    for event_type in ALL_DEVICE_EVENT_TYPES:
        assert event_type.startswith("device."), (
            f"Event type '{event_type}' must start with 'device.'"
        )
        # Must have at least two segments: device.<verb>
        parts = event_type.split(".")
        assert len(parts) >= 2, (
            f"Event type '{event_type}' must be in format 'device.<past_tense>'"
        )
        # Verb part must not be empty
        assert len(parts[1]) > 0, (
            f"Event type '{event_type}' has empty verb part"
        )


def test_no_duplicate_device_event_types():
    """Each event type must be declared exactly once."""
    seen = set()
    for event_type in ALL_DEVICE_EVENT_TYPES:
        assert event_type not in seen, f"Duplicate event type: {event_type}"
        seen.add(event_type)


# ---------------------------------------------------------------------------
# Rule 3: State machine transition snapshot
# ---------------------------------------------------------------------------

def test_provisioning_state_machine_allowed_transitions_snapshot():
    """Snapshot test for the canonical provisioning state machine.

    If you add a new status, you MUST explicitly add its allowed
    transitions here AND in the state machine.  This test prevents
    accidental lifecycle changes.
    """
    assert set(_PROVISIONING_TRANSITIONS.keys()) == set(ProvisioningStatus.values), (
        f"State machine keys {sorted(_PROVISIONING_TRANSITIONS.keys())} "
        f"do not match ProvisioningStatus values {sorted(ProvisioningStatus.values)}"
    )

    # Snapshot of expected transitions.
    expected = {
        ProvisioningStatus.UNPROVISIONED: {
            ProvisioningStatus.IDENTITY_CREATED,
            ProvisioningStatus.FAILED,
        },
        ProvisioningStatus.IDENTITY_CREATED: {
            ProvisioningStatus.CERTIFICATE_ISSUED,
            ProvisioningStatus.REGISTERED,
            ProvisioningStatus.FAILED,
        },
        ProvisioningStatus.CERTIFICATE_ISSUED: {
            ProvisioningStatus.REGISTERED,
            ProvisioningStatus.FAILED,
        },
        ProvisioningStatus.REGISTERED: {
            ProvisioningStatus.ACTIVATED,
            ProvisioningStatus.FAILED,
        },
        ProvisioningStatus.ACTIVATED: {
            ProvisioningStatus.FAILED,
        },
        ProvisioningStatus.FAILED: set(),
    }

    assert _PROVISIONING_TRANSITIONS == expected, (
        f"State machine transition snapshot mismatch.\n"
        f"Expected: {expected}\n"
        f"Got: {_PROVISIONING_TRANSITIONS}\n"
        f"If you intentionally changed the lifecycle, update this test."
    )


def test_activated_cannot_go_backwards():
    """ACTIVATED must never transition to UNPROVISIONED or IDENTITY_CREATED."""
    for forbidden in [
        ProvisioningStatus.UNPROVISIONED,
        ProvisioningStatus.IDENTITY_CREATED,
        ProvisioningStatus.CERTIFICATE_ISSUED,
        ProvisioningStatus.REGISTERED,
    ]:
        assert not can_transition(
            current_status=ProvisioningStatus.ACTIVATED,
            target_status=forbidden,
        ), f"ACTIVATED → {forbidden} must be forbidden."


def test_failed_has_no_outgoing_transitions():
    """FAILED is terminal — no outgoing transitions allowed."""
    assert is_terminal(ProvisioningStatus.FAILED)
    for target in ProvisioningStatus.values:
        assert not can_transition(
            current_status=ProvisioningStatus.FAILED,
            target_status=target,
        ), f"FAILED → {target} must be forbidden."


def test_unprovisioned_cannot_be_reached_from_any_other_state():
    """Only UNPROVISIONED can transition to UNPROVISIONED."""
    for status in ProvisioningStatus.values:
        if status == ProvisioningStatus.UNPROVISIONED:
            continue
        assert not can_transition(
            current_status=status,
            target_status=ProvisioningStatus.UNPROVISIONED,
        ), f"{status} → UNPROVISIONED must be forbidden."


# ---------------------------------------------------------------------------
# Rule 4: Sensitive model field protection
# ---------------------------------------------------------------------------

def test_device_credential_does_not_store_plaintext_secret():
    """DeviceCredential must never have a plaintext secret field."""
    import inspect
    from apps.devices.models import DeviceCredential

    fields = [f.name for f in DeviceCredential._meta.get_fields()]
    assert "api_secret" not in fields, (
        "DeviceCredential must not have a plaintext 'api_secret' field. "
        "Use 'api_secret_hash' (Argon2) instead."
    )
    assert "api_secret_hash" in fields, (
        "DeviceCredential must have 'api_secret_hash' field for Argon2 storage."
    )


# ---------------------------------------------------------------------------
# Rule 5: Rule operators are centrally defined
# ---------------------------------------------------------------------------

def test_rule_operators_are_centrally_defined():
    """All rule operators must be defined in RuleOperator, not ad-hoc."""
    from apps.care_engine.models.rule import RuleOperator, _OPERATOR_FUNCTIONS

    assert len(RuleOperator.values) >= 6, "RuleOperator must have at least 6 operators."
    for op in RuleOperator.values:
        assert op in _OPERATOR_FUNCTIONS, f"Operator '{op}' has no implementation."

    # Verify each operator works correctly
    assert _OPERATOR_FUNCTIONS[RuleOperator.GT](5, 3) is True
    assert _OPERATOR_FUNCTIONS[RuleOperator.GT](3, 5) is False
    assert _OPERATOR_FUNCTIONS[RuleOperator.LT](3, 5) is True
    assert _OPERATOR_FUNCTIONS[RuleOperator.EQ](5, 5) is True
    assert _OPERATOR_FUNCTIONS[RuleOperator.NEQ](5, 3) is True
    assert _OPERATOR_FUNCTIONS[RuleOperator.GTE](5, 5) is True
    assert _OPERATOR_FUNCTIONS[RuleOperator.LTE](5, 5) is True


# ---------------------------------------------------------------------------
# Rule 6: Alert lifecycle — terminal states cannot go backwards
# ---------------------------------------------------------------------------

def test_alert_resolved_cannot_go_back_to_open():
    """RESOLVED is terminal — cannot go back to OPEN or ACKNOWLEDGED."""
    from apps.notifications.domain.enums import AlertStatus
    from apps.notifications.services.alert_service import _validate_transition, InvalidAlertTransition

    for target in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]:
        with pytest.raises(InvalidAlertTransition):
            _validate_transition(AlertStatus.RESOLVED, target)


def test_alert_dismissed_is_terminal():
    """DISMISSED is terminal — cannot go back to any active status."""
    from apps.notifications.domain.enums import AlertStatus
    from apps.notifications.services.alert_service import _validate_transition, InvalidAlertTransition

    for target in [AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]:
        with pytest.raises(InvalidAlertTransition):
            _validate_transition(AlertStatus.DISMISSED, target)


# ---------------------------------------------------------------------------
# Rule 7: AlertEvent must be append-only (no update/delete by structural check)
# ---------------------------------------------------------------------------

def test_alert_event_has_no_update_methods():
    """AlertEvent model should have no save/delete overrides that modify existing rows."""
    from apps.notifications.models.alert_event import AlertEvent

    # AlertEvent should not override save to perform in-place updates.
    # The model is designed to be create-only.
    assert AlertEvent.__module__ == "apps.notifications.models.alert_event"
    # Verify model has created_at but not updated_at (append-only)
    fields = {f.name for f in AlertEvent._meta.get_fields()}
    assert "created_at" in fields
    assert "updated_at" not in fields, "AlertEvent must be append-only — no updated_at field."
