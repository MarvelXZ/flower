"""Compact mobile-friendly serializers for the provider dashboard.

Designed for low-bandwidth mobile networks:
- No heavy nested objects
- Only mobile-relevant fields
- IDs instead of full related objects
- ISO8601 timestamps
- Minimal payload size
"""

from rest_framework import serializers

from apps.provider_ops.models import ProviderTask, TaskSLA


class CompactTaskSerializer(serializers.ModelSerializer):
    """Lightweight list serializer for mobile task lists."""

    escalation_level = serializers.SerializerMethodField()
    sla_breached = serializers.SerializerMethodField()

    class Meta:
        model = ProviderTask
        fields = [
            "id",
            "title",
            "status",
            "priority",
            "task_type",
            "due_at",
            "escalation_level",
            "sla_breached",
            "created_at",
        ]

    def get_escalation_level(self, obj) -> int:
        try:
            return obj.sla.escalation_level
        except (AttributeError, TaskSLA.DoesNotExist):
            return 0

    def get_sla_breached(self, obj) -> bool:
        try:
            sla = obj.sla
            return sla.breached_response_sla or sla.breached_resolution_sla
        except (AttributeError, TaskSLA.DoesNotExist):
            return False


class CompactSLASerializer(serializers.ModelSerializer):
    """Compact SLA summary for mobile display."""

    class Meta:
        model = TaskSLA
        fields = [
            "response_due_at",
            "resolution_due_at",
            "breached_response_sla",
            "breached_resolution_sla",
            "escalation_level",
        ]


class CompactTaskDetailSerializer(serializers.ModelSerializer):
    """Extended detail serializer — adds SLA info and event count."""

    sla = CompactSLASerializer(read_only=True)
    notes_count = serializers.SerializerMethodField()
    latest_event = serializers.SerializerMethodField()

    class Meta:
        model = ProviderTask
        fields = [
            "id",
            "title",
            "description",
            "status",
            "priority",
            "task_type",
            "assignee_id",
            "due_at",
            "started_at",
            "completed_at",
            "escalation_level",
            "sla_breached",
            "sla",
            "notes_count",
            "latest_event",
            "created_at",
            "updated_at",
        ]

    escalation_level = serializers.SerializerMethodField()
    sla_breached = serializers.SerializerMethodField()

    def get_escalation_level(self, obj) -> int:
        try:
            return obj.sla.escalation_level
        except (AttributeError, TaskSLA.DoesNotExist):
            return 0

    def get_sla_breached(self, obj) -> bool:
        try:
            sla = obj.sla
            return sla.breached_response_sla or sla.breached_resolution_sla
        except (AttributeError, TaskSLA.DoesNotExist):
            return False

    def get_notes_count(self, obj) -> int:
        try:
            return obj.notes.count()
        except Exception:
            return 0

    def get_latest_event(self, obj) -> dict | None:
        try:
            event = obj.events.order_by("-created_at").first()
            if event:
                return {"event_type": event.event_type, "created_at": event.created_at.isoformat()}
        except Exception:
            pass
        return None
