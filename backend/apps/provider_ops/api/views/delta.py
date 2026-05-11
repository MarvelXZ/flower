"""Delta polling fallback endpoint for environments without WebSocket.

GET /api/provider/v1/dashboard/delta/?since=<iso_datetime>&limit=20
"""

from django.utils import timezone
from rest_framework.views import APIView

from apps.provider_ops.api.mobile_response import mobile_list_response
from apps.provider_ops.api.pagination import ProviderDashboardPagination
from apps.provider_ops.api.serializers.mobile import CompactTaskSerializer
from apps.provider_ops.domain.enums import ProviderTaskStatus
from apps.provider_ops.models import ProviderTask, RealtimeEvent


class DashboardDeltaView(APIView):
    """Return changes since a timestamp for polling fallback."""

    pagination_class = ProviderDashboardPagination

    def get(self, request):
        since_str = request.query_params.get("since", "")
        tenant_schema = getattr(request, "tenant", None)
        schema_name = getattr(tenant_schema, "schema_name", "") if tenant_schema else ""

        since = None
        if since_str:
            try:
                since = timezone.datetime.fromisoformat(since_str)
            except (ValueError, TypeError):
                pass

        # Changed tasks
        task_qs = ProviderTask.objects.select_related("sla").filter(
            status__in={
                ProviderTaskStatus.OPEN,
                ProviderTaskStatus.ASSIGNED,
                ProviderTaskStatus.IN_PROGRESS,
            },
        )
        if since:
            task_qs = task_qs.filter(updated_at__gte=since)

        # Recent realtime events
        event_qs = RealtimeEvent.objects.filter(tenant_schema=schema_name)
        if since:
            event_qs = event_qs.filter(created_at__gte=since)

        latest_event = event_qs.order_by("-created_at").first()
        event_count = event_qs.count()

        return mobile_list_response(
            paginator=self.pagination_class(),
            queryset=task_qs,
            serializer_class=CompactTaskSerializer,
            request=request,
            extra_meta={
                "delta": True,
                "since": since.isoformat() if since else "",
                "latest_event_id": latest_event.pk if latest_event else None,
                "latest_event_at": latest_event.created_at.isoformat() if latest_event else None,
                "event_count": event_count,
            },
        )
