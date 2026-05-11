from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.notifications.models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ["recipient", "channel", "subject", "status", "sent_at", "created_at"]
    list_filter = ["channel", "status", "created_at"]
    search_fields = ["recipient__username", "subject", "body"]
    readonly_fields = ["created_at", "updated_at"]
