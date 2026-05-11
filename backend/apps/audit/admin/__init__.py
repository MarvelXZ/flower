from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["actor", "action", "target_type", "target_id", "created_at"]
    list_filter = ["action", "created_at"]
    search_fields = ["target_type", "target_id", "actor__username"]
    readonly_fields = ["created_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
