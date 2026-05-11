from rest_framework import serializers

from apps.provider_ops.models import ProviderTask


class AlertUpsertSerializer(serializers.Serializer):
    source_owner_tenant_id = serializers.CharField(max_length=120)
    external_alert_id = serializers.CharField(max_length=255)
    rule_code = serializers.CharField(max_length=64)
    severity = serializers.CharField(max_length=16)
    status = serializers.CharField(max_length=16)
    title = serializers.CharField(max_length=255)
    message = serializers.CharField(required=False, allow_blank=True, default="")
    external_location_id = serializers.CharField(max_length=255, required=False, allow_null=True, default=None)
    external_plant_id = serializers.CharField(max_length=255, required=False, allow_null=True, default=None)
    external_device_id = serializers.CharField(max_length=255, required=False, allow_null=True, default=None)
    metadata = serializers.JSONField(required=False, default=dict)


class ProviderTaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderTask
        fields = [
            "id", "task_key", "task_type", "priority", "status",
            "title", "assignee_id", "due_at", "started_at", "completed_at",
            "created_at",
        ]


class ProviderTaskDetailSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    class Meta:
        model = ProviderTask
        fields = "__all__"

    def get_events(self, obj):
        return [
            {"event_type": e.event_type, "actor_id": e.actor_id, "message": e.message, "created_at": e.created_at.isoformat()}
            for e in obj.events.all()
        ]

    def get_notes(self, obj):
        return [
            {"id": n.pk, "actor_id": n.actor_id, "body": n.body, "created_at": n.created_at.isoformat()}
            for n in obj.notes.all()
        ]


class TaskActionSerializer(serializers.Serializer):
    assignee_id = serializers.CharField(max_length=255, required=False, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
