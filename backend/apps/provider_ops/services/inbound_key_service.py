from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.provider_ops.domain.enums import InboundKeyStatus
from apps.provider_ops.models import ProviderInboundKey


class InboundKeyError(ValueError):
    """Base error for inbound key service failures."""


class InboundKeyUnavailable(InboundKeyError):
    """Raised when no usable inbound key can be found."""


class InboundKeyScopeError(InboundKeyError):
    """Raised when the inbound key does not allow the requested scope."""


@dataclass(frozen=True)
class SettingsInboundKey:
    """Test/dev key model backed by Django settings."""

    key_id: str
    source_owner_tenant_id: str
    secret_reference: str
    status: str = InboundKeyStatus.ACTIVE
    valid_from: object | None = None
    valid_until: object | None = None
    scopes: list[str] | None = None


def _coerce_datetime(value):
    if not value:
        return None
    if hasattr(value, "tzinfo"):
        return value
    parsed = parse_datetime(str(value))
    if parsed and timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _is_inbound_key_usable(key, *, now=None) -> bool:
    """Return True if the key is active and within its validity window."""
    current_time = now or timezone.now()
    if key.status != InboundKeyStatus.ACTIVE:
        return False
    valid_from = _coerce_datetime(getattr(key, "valid_from", None))
    valid_until = _coerce_datetime(getattr(key, "valid_until", None))
    if valid_from and valid_from > current_time:
        return False
    if valid_until and valid_until <= current_time:
        return False
    return True


def _key_has_scope(key, *, required_scope: str) -> bool:
    """Return True if the key's scopes allow the required scope."""
    key_scopes = getattr(key, "scopes", None) or []
    if not required_scope:
        return True
    return required_scope in key_scopes


# ---------------------------------------------------------------------------
# Registry-backed lookup  (provider tenant schema)
# ---------------------------------------------------------------------------


def register_inbound_key(
    *,
    key_id: str,
    source_owner_tenant_id: str,
    secret_reference: str,
    valid_from=None,
    valid_until=None,
    scopes: list[str] | None = None,
) -> ProviderInboundKey:
    """Register a new active inbound key in the provider tenant schema."""
    now = timezone.now()
    with transaction.atomic():
        key = ProviderInboundKey.objects.create(
            key_id=key_id,
            source_owner_tenant_id=source_owner_tenant_id,
            secret_reference=secret_reference,
            status=InboundKeyStatus.ACTIVE,
            valid_from=valid_from or now,
            valid_until=valid_until,
            scopes=scopes or [],
        )
        return key


def revoke_inbound_key(*, key_id: str) -> ProviderInboundKey:
    """Revoke an inbound key so it can no longer authenticate requests."""
    now = timezone.now()
    with transaction.atomic():
        key = ProviderInboundKey.objects.select_for_update().get(key_id=key_id)
        key.status = InboundKeyStatus.REVOKED
        key.revoked_at = now
        key.save(update_fields=["status", "revoked_at"])
        return key


def get_active_inbound_key(*, key_id: str, now=None) -> ProviderInboundKey:
    """Return the active, non-expired inbound key by public key id.

    First tries the database (provider tenant schema).  Falls back to
    settings-backed lookup **only** when a specific test-mode flag is set.
    """
    current_time = now or timezone.now()

    try:
        key = ProviderInboundKey.objects.get(
            key_id=key_id,
            status=InboundKeyStatus.ACTIVE,
            valid_from__lte=current_time,
        )
        if key.valid_until and key.valid_until <= current_time:
            raise InboundKeyUnavailable("Inbound key is expired.")
        return key
    except ProviderInboundKey.DoesNotExist:
        pass

    # Settings fallback — only active when B2B_USE_SETTINGS_KEY is True
    use_settings = getattr(settings, "B2B_USE_SETTINGS_KEY", False)
    if use_settings:
        return get_settings_inbound_key(key_id=key_id, now=now)

    raise InboundKeyUnavailable("Inbound key is unknown, revoked, or expired.")


def validate_inbound_key_scope(*, key, required_scope: str) -> None:
    """Raise ``InboundKeyScopeError`` if the key does not allow the scope."""
    if not _key_has_scope(key, required_scope=required_scope):
        raise InboundKeyScopeError(
            f"Inbound key '{key.key_id}' does not have scope '{required_scope}'.",
        )


# ---------------------------------------------------------------------------
# Settings-backed fallback  (test/dev only)
# ---------------------------------------------------------------------------


def get_settings_inbound_key(*, key_id: str, now=None) -> SettingsInboundKey:
    """Test/dev inbound key lookup backed by Django settings."""
    expected_key_id = getattr(settings, "B2B_TEST_KEY_ID", "")
    if key_id != expected_key_id:
        raise InboundKeyUnavailable("Inbound key is unknown, revoked, or expired.")

    key = SettingsInboundKey(
        key_id=expected_key_id,
        source_owner_tenant_id=getattr(settings, "B2B_TEST_SOURCE_OWNER_TENANT_ID", ""),
        secret_reference=getattr(settings, "B2B_TEST_SECRET_REFERENCE", ""),
        status=getattr(settings, "B2B_TEST_KEY_STATUS", InboundKeyStatus.ACTIVE),
        valid_from=_coerce_datetime(getattr(settings, "B2B_TEST_KEY_VALID_FROM", "")),
        valid_until=_coerce_datetime(getattr(settings, "B2B_TEST_KEY_VALID_UNTIL", "")),
        scopes=getattr(settings, "B2B_TEST_KEY_SCOPES", None),
    )
    if not _is_inbound_key_usable(key, now=now):
        raise InboundKeyUnavailable("Inbound key is unknown, revoked, or expired.")
    return key
