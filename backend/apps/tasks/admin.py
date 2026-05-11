from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "task_type", "status", "priority", "assigned_to", "source", "due_date"]
    list_filter = ["status", "priority", "task_type", "source", "created_at"]
    search_fields = ["title", "description"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "created_at"
