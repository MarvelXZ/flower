"""
Device authentication for the PlantOps API.

Provides DRF authentication class that validates device requests
using API key + HMAC signature pattern.

Usage in DRF views:
    authentication_classes = [DeviceApiKeyAuthentication]
"""

import hashlib
import hmac
import time

from django.utils.translation import gettext_lazy as _
from rest_framework import authentication, exceptions

from apps.devices.models import DeviceCredential


class DeviceApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate IoT devices via API key and HMAC signature.

    Request headers:
        X-Device-Key: <api_key>
        X-Device-Timestamp: <unix_timestamp>
        X-Device-Signature: <hmac_sha256_hex(api_key + timestamp + body, api_secret)>

    The api_secret is NEVER transmitted. The device computes an HMAC
    of the request using the shared secret, and the server verifies it.

    Timestamp validation prevents replay attacks (default window: 5 minutes).
    """

    TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes

    def authenticate(self, request):
        api_key = request.META.get("HTTP_X_DEVICE_KEY")
        timestamp = request.META.get("HTTP_X_DEVICE_TIMESTAMP")
        signature = request.META.get("HTTP_X_DEVICE_SIGNATURE")

        if not api_key:
            return None  # Let other auth classes handle this request

        if not timestamp or not signature:
            raise exceptions.AuthenticationFailed(
                _("Device authentication requires X-Device-Key, X-Device-Timestamp, and X-Device-Signature headers.")
            )

        # Validate timestamp to prevent replay attacks
        try:
            ts = int(timestamp)
        except (ValueError, TypeError):
            raise exceptions.AuthenticationFailed(_("Invalid timestamp format."))

        now = int(time.time())
        if abs(now - ts) > self.TIMESTAMP_TOLERANCE_SECONDS:
            raise exceptions.AuthenticationFailed(_("Request timestamp outside acceptable window."))

        # Look up the credential
        try:
            credential = DeviceCredential.objects.select_related("device").get(
                api_key=api_key,
                is_active=True,
            )
        except DeviceCredential.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid device API key."))

        # Verify the device is active
        if not credential.device.is_active:
            raise exceptions.AuthenticationFailed(_("Device is inactive."))

        # Verify HMAC signature
        if not self._verify_signature(credential, timestamp, request.body, signature):
            raise exceptions.AuthenticationFailed(_("Invalid device signature."))

        # Update last_used_at (fire-and-forget, don't block auth)
        credential.save(update_fields=["last_used_at"])

        return (credential.device, credential)

    def authenticate_header(self, request):
        return "DeviceApiKey"

    @staticmethod
    def _verify_signature(credential, timestamp, body, provided_signature):
        """
        Verify HMAC-SHA256 signature.

        The message is: api_key + timestamp + request_body
        The key is the stored api_secret (plain text, compared via hmac.compare_digest).
        """
        message = f"{credential.api_key}{timestamp}".encode() + body
        expected = hmac.new(
            credential.api_secret.encode(),
            message,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, provided_signature)
