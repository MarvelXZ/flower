from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.automation.models import AutomationRule, AutomationExecution


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "trigger_type", "action_type", "is_active", "created_at"]
    list_filter = ["trigger_type", "action_type", "is_active"]
    search_fields = ["name"]


@admin.register(AutomationExecution)
class AutomationExecutionAdmin(admin.ModelAdmin):
    list_display = ["rule", "status", "triggered_by", "started_at", "completed_at"]
    list_filter = ["status", "started_at"]
    readonly_fields = ["started_at"]
