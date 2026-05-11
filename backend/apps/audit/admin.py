from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["actor", "action", "target_type", "target_id", "occurred_at"]
    list_filter = ["action", "occurred_at"]
    search_fields = ["target_type", "target_id", "actor__username"]
    readonly_fields = ["occurred_at", "created_at", "updated_at"]
    date_hierarchy = "occurred_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
