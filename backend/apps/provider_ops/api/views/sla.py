from rest_framework.response import Response
from rest_framework.views import APIView

from apps.provider_ops.api.mobile_response import mobile_list_response
from apps.provider_ops.api.pagination import ProviderDashboardPagination
from apps.provider_ops.api.serializers.mobile import CompactTaskSerializer
from apps.provider_ops.selectors.sla_selectors import (
    list_breached_tasks,
    list_overdue_tasks,
    sla_dashboard_summary,
)
from apps.provider_ops.selectors.task_selectors import task_dashboard_summary as task_summary


class SLASummaryView(APIView):
    """GET /api/provider/v1/sla/summary/ — SLA dashboard metrics."""

    def get(self, request):
        sla = sla_dashboard_summary()
        tasks = task_summary()
        return Response({
            "sla": sla,
            "tasks": tasks,
            "meta": {"generated_at": __import__("django.utils.timezone", fromlist=["timezone"]).timezone.now().isoformat()},
        })


class OverdueTaskListView(APIView):
    """GET /api/provider/v1/tasks/overdue/ — paginated overdue tasks list."""

    pagination_class = ProviderDashboardPagination

    def get(self, request):
        qs = list_overdue_tasks().select_related("sla")
        return mobile_list_response(
            paginator=self.pagination_class(),
            queryset=qs,
            serializer_class=CompactTaskSerializer,
            request=request,
        )


class BreachedTaskListView(APIView):
    """GET /api/provider/v1/tasks/breached/ — paginated breached tasks list."""

    pagination_class = ProviderDashboardPagination

    def get(self, request):
        qs = list_breached_tasks().select_related("sla")
        return mobile_list_response(
            paginator=self.pagination_class(),
            queryset=qs,
            serializer_class=CompactTaskSerializer,
            request=request,
        )
