from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.billing.models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["plan", "billing_cycle", "start_date", "end_date", "max_devices", "max_planters", "is_active"]
    list_filter = ["plan", "billing_cycle", "is_active"]
    readonly_fields = ["created_at", "updated_at"]
