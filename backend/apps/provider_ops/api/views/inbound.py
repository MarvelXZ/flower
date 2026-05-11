from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.provider_ops.api.authentication import B2BProviderAuthentication
from apps.provider_ops.api.serializers import (
    DeviceUpsertSerializer,
    LocationUpsertSerializer,
    TelemetryBatchSerializer,
)
from apps.provider_ops.services import idempotency_service, inbound_service


class B2BAPIView(APIView):
    authentication_classes = [B2BProviderAuthentication]

    def _idempotency_key(self):
        return self.request.headers.get("X-Idempotency-Key")

    def _auth_source_owner(self) -> str | None:
        """Return ``source_owner_tenant_id`` from the authenticated request, if set."""
        return getattr(self.request, "b2b_source_owner_tenant_id", None)

    def _execute_idempotent(self, *, payload, handler):
        try:
            result = idempotency_service.execute_idempotent_request(
                key=self._idempotency_key(),
                endpoint=self.request.path,
                payload=payload,
                handler=handler,
            )
        except idempotency_service.MissingIdempotencyKey as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except idempotency_service.IdempotencyConflict as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        response = Response(result.response_body, status=result.response_status)
        if result.cached:
            response["X-Idempotent-Replay"] = "true"
        return response


class LocationUpsertView(B2BAPIView):
    def post(self, request):
        serializer = LocationUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        effective_source = inbound_service.validate_source_owner_id(
            auth_source_owner_tenant_id=self._auth_source_owner(),
            payload_source_owner_tenant_id=data["source_owner_tenant_id"],
        )

        def handler():
            location, created = inbound_service.upsert_external_location(
                source_owner_tenant_id=effective_source,
                external_id=data["external_id"],
                name=data["name"],
                address=data.get("address", ""),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                raw_payload=data.get("raw_payload"),
            )
            return (
                status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                {
                    "external_id": location.external_id,
                    "source_owner_tenant_id": location.source_owner_tenant_id,
                    "created": created,
                },
            )

        return self._execute_idempotent(payload=request.data, handler=handler)


class DeviceUpsertView(B2BAPIView):
    def post(self, request):
        serializer = DeviceUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        effective_source = inbound_service.validate_source_owner_id(
            auth_source_owner_tenant_id=self._auth_source_owner(),
            payload_source_owner_tenant_id=data["source_owner_tenant_id"],
        )

        def handler():
            try:
                device, created = inbound_service.upsert_external_device(
                    source_owner_tenant_id=effective_source,
                    external_id=data["external_id"],
                    name=data["name"],
                    status=data["status"],
                    external_location_id=data.get("external_location_id"),
                    raw_payload=data.get("raw_payload"),
                )
            except inbound_service.UnknownExternalLocationError as exc:
                return status.HTTP_400_BAD_REQUEST, {"detail": str(exc)}

            return (
                status.HTTP_201_CREATED if created else status.HTTP_200_OK,
                {
                    "external_id": device.external_id,
                    "source_owner_tenant_id": device.source_owner_tenant_id,
                    "created": created,
                },
            )

        return self._execute_idempotent(payload=request.data, handler=handler)


class TelemetryBatchView(B2BAPIView):
    def post(self, request):
        serializer = TelemetryBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        effective_source = inbound_service.validate_source_owner_id(
            auth_source_owner_tenant_id=self._auth_source_owner(),
            payload_source_owner_tenant_id=data["source_owner_tenant_id"],
        )

        def handler():
            try:
                ingested = inbound_service.ingest_telemetry_batch(
                    source_owner_tenant_id=effective_source,
                    readings=data["readings"],
                )
            except inbound_service.UnknownExternalDeviceError as exc:
                return status.HTTP_400_BAD_REQUEST, {"detail": str(exc)}

            return (
                status.HTTP_202_ACCEPTED,
                {
                    "accepted": len(ingested),
                    "source_owner_tenant_id": effective_source,
                },
            )

        return self._execute_idempotent(payload=request.data, handler=handler)


class SyncStatusView(B2BAPIView):
    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
