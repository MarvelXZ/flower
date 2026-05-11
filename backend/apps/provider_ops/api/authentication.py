import hmac
from dataclasses import dataclass

from django.conf import settings
from rest_framework import authentication, exceptions

from apps.integrations.services.hmac_signing_service import (
    HMAC_KEY_ID_HEADER,
    HMAC_SIGNATURE_HEADER,
    HMAC_TIMESTAMP_HEADER,
    IDEMPOTENCY_KEY_HEADER,
    HMACVerificationError,
    verify_hmac_signature,
)
from apps.integrations.services.secret_resolver import SecretNotFound, SettingsSecretResolver, resolve_secret
from apps.provider_ops.services.inbound_key_service import (
    InboundKeyScopeError,
    InboundKeyUnavailable,
    get_active_inbound_key,
    validate_inbound_key_scope,
)

# Maps request path prefixes to the required inbound key scope.
ENDPOINT_SCOPE_MAP: dict[str, str] = {
    "/api/b2b/v1/locations/": "locations:write",
    "/api/b2b/v1/devices/": "devices:write",
    "/api/b2b/v1/telemetry/": "telemetry:write",
}


def _resolve_required_scope(path: str) -> str | None:
    """Return the required scope for ``path``, or ``None`` if unknown."""
    for prefix, scope in ENDPOINT_SCOPE_MAP.items():
        if path.startswith(prefix):
            return scope
    return None


@dataclass(frozen=True)
class B2BPrincipal:
    name: str = "provider-b2b"
    is_authenticated: bool = True


class B2BProviderAuthentication(authentication.BaseAuthentication):
    """Provider inbound authentication with legacy test API key and HMAC support.

    HMAC authentication flow:
    1.  Look up ``ProviderInboundKey`` via ``X-B2B-Key-Id`` (provider tenant
        schema registry, with optional settings fallback in test mode).
    2.  Verify key status is ``active`` and within the validity window.
    3.  Resolve the shared secret via ``secret_reference``.
    4.  Verify the HMAC signature.
    5.  Validate that the key's scopes allow the target endpoint.
    6.  Attach ``source_owner_tenant_id`` to the request as
        ``request.b2b_source_owner_tenant_id`` for downstream views.
    """

    header_name = "HTTP_X_PROVIDER_API_KEY"

    def authenticate(self, request):
        django_request = getattr(request, "_request", request)
        provided_key = django_request.META.get(self.header_name)
        if provided_key is not None:
            return self._authenticate_test_api_key(provided_key)

        return self._authenticate_hmac(django_request)

    def _authenticate_test_api_key(self, provided_key: str):
        expected_key = getattr(settings, "B2B_TEST_API_KEY", "")

        if not expected_key:
            raise exceptions.AuthenticationFailed("Missing provider API key.")

        if not hmac.compare_digest(provided_key, expected_key):
            raise exceptions.AuthenticationFailed("Invalid provider API key.")

        return B2BPrincipal(), None

    def _authenticate_hmac(self, request):
        meta = request.META
        key_id = meta.get(f"HTTP_{HMAC_KEY_ID_HEADER.upper().replace('-', '_')}")

        if not key_id:
            raise exceptions.AuthenticationFailed("Missing X-B2B-Key-Id header.")

        try:
            # Step 1-2: Look up active inbound key (registry, with optional
            # settings fallback in test mode).
            inbound_key = get_active_inbound_key(key_id=key_id)

            # Step 3: Resolve the shared secret.
            shared_secret = resolve_secret(
                inbound_key.secret_reference,
                resolver=SettingsSecretResolver(),
            )

            # Step 4: Verify the HMAC signature.
            verify_hmac_signature(
                method=request.method,
                path=request.path,
                body_bytes=request.body,
                idempotency_key=meta.get(f"HTTP_{IDEMPOTENCY_KEY_HEADER.upper().replace('-', '_')}"),
                key_id=key_id,
                timestamp=meta.get(f"HTTP_{HMAC_TIMESTAMP_HEADER.upper().replace('-', '_')}"),
                signature=meta.get(f"HTTP_{HMAC_SIGNATURE_HEADER.upper().replace('-', '_')}"),
                expected_key_id=inbound_key.key_id,
                shared_secret=shared_secret,
                max_skew_seconds=getattr(settings, "B2B_HMAC_MAX_SKEW_SECONDS", 300),
            )

            # Step 5: Validate scope for the endpoint.
            required_scope = _resolve_required_scope(request.path)
            if required_scope:
                validate_inbound_key_scope(key=inbound_key, required_scope=required_scope)

        except (InboundKeyUnavailable, SecretNotFound, HMACVerificationError, InboundKeyScopeError) as exc:
            raise exceptions.AuthenticationFailed(str(exc)) from exc

        # Step 6: Attach source_owner_tenant_id for downstream views.
        request.b2b_source_owner_tenant_id = inbound_key.source_owner_tenant_id

        return B2BPrincipal(), None

    def authenticate_header(self, request):
        return "ProviderApiKey, B2B-HMAC"
