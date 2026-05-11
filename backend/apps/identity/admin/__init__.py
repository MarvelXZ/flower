from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.identity.models import User


@admin.register(User)
class IdentityUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Tenant profile", {"fields": ("role", "language", "timezone")}),
    )
    list_display = ["username", "email", "role", "is_staff", "is_active"]
    list_filter = UserAdmin.list_filter + ("role",)
