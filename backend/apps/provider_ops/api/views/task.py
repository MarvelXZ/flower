from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.provider_ops.api.authentication import B2BProviderAuthentication
from apps.provider_ops.api.filters.task_filters import TaskFilter
from apps.provider_ops.api.mobile_response import mobile_list_response
from apps.provider_ops.api.pagination import ProviderDashboardPagination
from apps.provider_ops.api.serializers.mobile import CompactTaskSerializer
from apps.provider_ops.api.serializers.task import (
    AlertUpsertSerializer,
    ProviderTaskDetailSerializer,
    TaskActionSerializer,
)
from apps.provider_ops.models import ProviderTask
from apps.provider_ops.selectors.task_selectors import list_open_tasks
from apps.provider_ops.services.alert_task_mapper import build_task_key, map_alert_to_task_payload
from apps.provider_ops.services.inbound_service import validate_source_owner_id
from apps.provider_ops.services.task_service import (
    add_task_note,
    assign_task,
    cancel_task,
    complete_task,
    create_task,
    start_task,
)


# ---------------------------------------------------------------------------
# Ordering helper
# ---------------------------------------------------------------------------

_ORDERING_FIELDS = {
    "created_at": "created_at",
    "-created_at": "-created_at",
    "due_at": "due_at",
    "-due_at": "-due_at",
    "priority": None,  # handled separately
    "-priority": None,
    "updated_at": "updated_at",
    "-updated_at": "-updated_at",
    "escalation_level": "sla__escalation_level",
    "-escalation_level": "-sla__escalation_level",
}


def _apply_ordering(qs, ordering_param: str):
    """Apply ordering with fallback: urgent first, overdue first, newest first."""
    if ordering_param in _ORDERING_FIELDS:
        mapped = _ORDERING_FIELDS[ordering_param]
        if mapped:
            return qs.order_by(mapped)
        elif ordering_param == "priority":
            return qs.order_by("-priority")
        elif ordering_param == "-priority":
            return qs.order_by("priority")

    # Default: urgent first, then overdue, then newest
    return qs.order_by(
        "-priority",
        "sla__resolution_due_at",
        "-created_at",
    )


# ---------------------------------------------------------------------------
# B2B inbound
# ---------------------------------------------------------------------------


class AlertUpsertView(APIView):
    """Provider inbound B2B endpoint to upsert an alert as a task.

    POST /api/b2b/v1/alerts/upsert/
    """

    authentication_classes = [B2BProviderAuthentication]

    def post(self, request):
        serializer = AlertUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        auth_source = getattr(request, "b2b_source_owner_tenant_id", None)
        effective = validate_source_owner_id(
            auth_source_owner_tenant_id=auth_source,
            payload_source_owner_tenant_id=data["source_owner_tenant_id"],
        )

        payload = map_alert_to_task_payload(
            rule_code=data["rule_code"],
            severity=data["severity"],
            title=data["title"],
            message=data.get("message", ""),
        )

        task_key = build_task_key(
            source_owner_tenant_id=effective,
            external_alert_id=data["external_alert_id"],
            task_type=payload.task_type,
        )

        task = create_task(
            task_key=task_key,
            source_owner_tenant_id=effective,
            task_type=payload.task_type,
            priority=payload.priority,
            title=payload.title,
            description=payload.description,
            external_alert_id=data["external_alert_id"],
            external_location_id=data.get("external_location_id") or "",
            external_plant_id=data.get("external_plant_id") or "",
            external_device_id=data.get("external_device_id") or "",
            metadata=data.get("metadata") or {},
        )

        return Response(
            {"task_id": task.pk, "task_key": task.task_key, "status": task.status, "created": task.created_at},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Provider dashboard API — mobile-ready
# ---------------------------------------------------------------------------


class ProviderTaskListView(APIView):
    """GET /api/provider/v1/tasks/

    Supports pagination (limit/offset), filtering, and sorting.
    Returns compact mobile-friendly payload.
    """

    pagination_class = ProviderDashboardPagination

    def get(self, request):
        qs = list_open_tasks().select_related("sla").prefetch_related("events")

        # Filtering
        qs = TaskFilter(request.query_params).apply(qs)

        # Sorting
        qs = _apply_ordering(qs, request.query_params.get("ordering", ""))

        return mobile_list_response(
            paginator=self.pagination_class(),
            queryset=qs,
            serializer_class=CompactTaskSerializer,
            request=request,
            extra_meta={"filtered": bool(request.query_params)},
        )


class ProviderTaskDetailView(APIView):
    """GET /api/provider/tasks/{id}/"""

    def get_object(self, pk):
        try:
            return ProviderTask.objects.get(pk=pk)
        except ProviderTask.DoesNotExist:
            return None

    def get(self, request, pk):
        task = self.get_object(pk)
        if task is None:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProviderTaskDetailSerializer(task)
        return Response(serializer.data)


class ProviderTaskAssignView(APIView):
    """POST /api/provider/tasks/{id}/assign/"""

    def post(self, request, pk):
        try:
            task = ProviderTask.objects.get(pk=pk)
        except ProviderTask.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = assign_task(task=task, assignee_id=serializer.validated_data.get("assignee_id", ""))
        return Response({"status": task.status, "assignee_id": task.assignee_id})


class ProviderTaskStartView(APIView):
    """POST /api/provider/tasks/{id}/start/"""

    def post(self, request, pk):
        try:
            task = ProviderTask.objects.get(pk=pk)
        except ProviderTask.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        task = start_task(task=task)
        return Response({"status": task.status})


class ProviderTaskCompleteView(APIView):
    """POST /api/provider/tasks/{id}/complete/"""

    def post(self, request, pk):
        try:
            task = ProviderTask.objects.get(pk=pk)
        except ProviderTask.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = complete_task(task=task, completion_note=serializer.validated_data.get("note", ""))
        return Response({"status": task.status})


class ProviderTaskCancelView(APIView):
    """POST /api/provider/tasks/{id}/cancel/"""

    def post(self, request, pk):
        try:
            task = ProviderTask.objects.get(pk=pk)
        except ProviderTask.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = cancel_task(task=task, reason=serializer.validated_data.get("reason", ""))
        return Response({"status": task.status})


class ProviderTaskAddNoteView(APIView):
    """POST /api/provider/tasks/{id}/notes/"""

    def post(self, request, pk):
        try:
            task = ProviderTask.objects.get(pk=pk)
        except ProviderTask.DoesNotExist:
            return Response({"detail": "Task not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = add_task_note(task=task, body=serializer.validated_data.get("note", ""))
        return Response({"note_id": note.pk}, status=status.HTTP_201_CREATED)
