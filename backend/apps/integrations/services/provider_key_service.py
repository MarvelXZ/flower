from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.integrations.domain.enums import ProviderKeyStatus
from apps.integrations.models import ProviderKey
from apps.integrations.services.integration_audit_service import audit_integration_event


class ProviderKeyLifecycleError(ValueError):
    """Raised when a provider key lifecycle command is invalid."""


class ProviderKeyUnavailable(LookupError):
    """Raised when no usable provider key can be found."""


@dataclass(frozen=True)
class SettingsProviderKey:
    key_id: str
    secret_reference: str
    status: str = ProviderKeyStatus.ACTIVE
    valid_from: object | None = None
    valid_until: object | None = None


def _coerce_datetime(value):
    if not value:
        return None
    if hasattr(value, "tzinfo"):
        return value
    parsed = parse_datetime(str(value))
    if parsed and timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone=timezone.get_current_timezone())
    return parsed


def is_provider_key_usable(key, *, now=None) -> bool:
    current_time = now or timezone.now()
    if key.status != ProviderKeyStatus.ACTIVE:
        return False
    valid_from = _coerce_datetime(getattr(key, "valid_from", None))
    valid_until = _coerce_datetime(getattr(key, "valid_until", None))
    if valid_from and valid_from > current_time:
        return False
    if valid_until and valid_until <= current_time:
        return False
    return True


def _ensure_no_active_key(*, provider_connection, now=None) -> None:
    try:
        get_active_key_for_connection(provider_connection=provider_connection, now=now)
    except ProviderKeyUnavailable:
        return
    raise ProviderKeyLifecycleError("Provider connection already has an active key.")


def create_provider_key(
    *,
    provider_connection,
    key_id: str,
    secret_reference: str,
    valid_from=None,
    valid_until=None,
    actor=None,
) -> ProviderKey:
    """Create the initial active key for a provider connection."""
    now = timezone.now()
    with transaction.atomic():
        _ensure_no_active_key(provider_connection=provider_connection, now=now)
        key = ProviderKey.objects.create(
            provider_connection=provider_connection,
            key_id=key_id,
            secret_reference=secret_reference,
            status=ProviderKeyStatus.ACTIVE,
            valid_from=valid_from or now,
            valid_until=valid_until,
        )
        audit_integration_event(
            event_type="key_created",
            target_type="ProviderKey",
            target_id=key_id,
            metadata={"provider_connection_id": getattr(provider_connection, "id", None)},
            actor=actor,
        )
        return key


def rotate_provider_key(
    *,
    provider_connection,
    new_key_id: str,
    new_secret_reference: str,
    valid_from=None,
    valid_until=None,
    actor=None,
) -> ProviderKey:
    """Rotate a provider connection key and make the new key active."""
    now = timezone.now()
    with transaction.atomic():
        old_key = get_active_key_for_connection(provider_connection=provider_connection, now=now)
        old_key.status = ProviderKeyStatus.ROTATED
        old_key.valid_until = now
        old_key.rotated_at = now
        old_key.save(update_fields=["status", "valid_until", "rotated_at"])

        new_key = ProviderKey.objects.create(
            provider_connection=provider_connection,
            key_id=new_key_id,
            secret_reference=new_secret_reference,
            status=ProviderKeyStatus.ACTIVE,
            valid_from=valid_from or now,
            valid_until=valid_until,
        )
        audit_integration_event(
            event_type="key_rotated",
            target_type="ProviderKey",
            target_id=new_key_id,
            metadata={
                "provider_connection_id": getattr(provider_connection, "id", None),
                "previous_key_id": old_key.key_id,
            },
            actor=actor,
        )
        return new_key


def revoke_provider_key(*, provider_key, actor=None) -> ProviderKey:
    """Revoke a provider key so it can no longer sign or verify requests."""
    now = timezone.now()
    with transaction.atomic():
        provider_key.status = ProviderKeyStatus.REVOKED
        provider_key.valid_until = now
        provider_key.revoked_at = now
        provider_key.save(update_fields=["status", "valid_until", "revoked_at"])
        audit_integration_event(
            event_type="key_revoked",
            target_type="ProviderKey",
            target_id=provider_key.key_id,
            metadata={
                "provider_connection_id": getattr(provider_key.provider_connection, "id", None),
            },
            actor=actor,
        )
        return provider_key


def get_active_key_for_connection(*, provider_connection, now=None):
    """Return the single active, non-expired key for a provider connection."""
    current_time = now or timezone.now()
    key = (
        ProviderKey.objects.filter(
            provider_connection=provider_connection,
            status=ProviderKeyStatus.ACTIVE,
            valid_from__lte=current_time,
        )
        .filter(valid_until__isnull=True)
        .order_by("-valid_from", "-created_at")
        .first()
    )
    if key:
        return key

    key = (
        ProviderKey.objects.filter(
            provider_connection=provider_connection,
            status=ProviderKeyStatus.ACTIVE,
            valid_from__lte=current_time,
            valid_until__gt=current_time,
        )
        .order_by("-valid_from", "-created_at")
        .first()
    )
    if not key:
        raise ProviderKeyUnavailable("No active provider key is available for this connection.")
    return key


def get_key_by_key_id(*, key_id: str, now=None):
    """Return an active, non-expired provider key by public key id."""
    current_time = now or timezone.now()
    key = (
        ProviderKey.objects.filter(
            key_id=key_id,
            status=ProviderKeyStatus.ACTIVE,
            valid_from__lte=current_time,
        )
        .filter(valid_until__isnull=True)
        .order_by("-valid_from", "-created_at")
        .first()
    )
    if key:
        return key

    key = (
        ProviderKey.objects.filter(
            key_id=key_id,
            status=ProviderKeyStatus.ACTIVE,
            valid_from__lte=current_time,
            valid_until__gt=current_time,
        )
        .order_by("-valid_from", "-created_at")
        .first()
    )
    if not key:
        raise ProviderKeyUnavailable("Provider key is unknown, revoked, or expired.")
    return key


def get_settings_key_by_key_id(*, key_id: str, now=None) -> SettingsProviderKey:
    """Provider-side test/dev key lookup backed by settings."""
    expected_key_id = getattr(settings, "B2B_TEST_KEY_ID", "")
    if key_id != expected_key_id:
        raise ProviderKeyUnavailable("Provider key is unknown, revoked, or expired.")

    key = SettingsProviderKey(
        key_id=expected_key_id,
        secret_reference=getattr(settings, "B2B_TEST_SECRET_REFERENCE", ""),
        status=getattr(settings, "B2B_TEST_KEY_STATUS", ProviderKeyStatus.ACTIVE),
        valid_from=_coerce_datetime(getattr(settings, "B2B_TEST_KEY_VALID_FROM", "")),
        valid_until=_coerce_datetime(getattr(settings, "B2B_TEST_KEY_VALID_UNTIL", "")),
    )
    if not is_provider_key_usable(key, now=now):
        raise ProviderKeyUnavailable("Provider key is unknown, revoked, or expired.")
    return key
