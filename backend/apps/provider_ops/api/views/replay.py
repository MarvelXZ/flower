"""Realtime event replay endpoint for reconnect/resume."""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.provider_ops.services.realtime_event_service import replay_events


class RealtimeReplayView(APIView):
    """GET /api/provider/v1/realtime/replay/?after=<event_id>&limit=100

    Returns a compact list of events since ``after`` for client catch-up.
    """

    def get(self, request):
        tenant = getattr(request, "tenant", None)
        schema_name = getattr(tenant, "schema_name", "") if tenant else ""
        after = request.query_params.get("after")
        limit = min(int(request.query_params.get("limit", 100)), 200)

        try:
            after_id = int(after) if after else None
        except (ValueError, TypeError):
            after_id = None

        events = replay_events(
            tenant_schema=schema_name,
            after_event_id=after_id,
            limit=limit,
        )

        return Response({
            "count": len(events),
            "events": events,
            "fallback_required": len(events) >= limit,
            "meta": {
                "request_id": getattr(request, "request_id", ""),
                "correlation_id": getattr(request, "correlation_id", ""),
            },
        })
