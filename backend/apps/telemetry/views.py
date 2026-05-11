"""
Telemetry views.

Provides the ingest endpoint for device telemetry data.
"""

from rest_framework import status, views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.devices.auth import DeviceApiKeyAuthentication
from apps.telemetry.serializers import TelemetryIngestSerializer
from apps.telemetry.services import ingest_telemetry


class TelemetryIngestView(views.APIView):
    """
    Accept telemetry data from authenticated IoT devices.

    POST /api/v1/telemetry/ingest/

    Authentication: Device API key + HMAC signature
    Rate limit: Apply via DRF throttling or nginx (future)

    The view validates the payload schema and hands off processing
    to the service layer, which handles deduplication, validation,
    and persistence.
    """

    authentication_classes = [DeviceApiKeyAuthentication]
    permission_classes = [AllowAny]  # Auth handled by DeviceApiKeyAuthentication

    def post(self, request):
        serializer = TelemetryIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # request.user is the Device instance (set by DeviceApiKeyAuthentication)
        device = request.user

        results = ingest_telemetry(
            device=device,
            payload=serializer.validated_data,
        )

        return Response(
            {
                "status": "accepted",
                "device_id": device.device_id,
                "processed": results["processed"],
                "skipped": results["skipped"],
                "errors": results["errors"],
            },
            status=status.HTTP_202_ACCEPTED,
        )
