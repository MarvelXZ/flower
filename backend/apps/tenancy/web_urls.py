from django.urls import path

from apps.tenancy.views import TenantCreateView, TenantListView, TenantUpdateView

app_name = "tenancy_ui"

urlpatterns = [
    path("", TenantListView.as_view(), name="tenant-list"),
    path("new/", TenantCreateView.as_view(), name="tenant-create"),
    path("<int:pk>/edit/", TenantUpdateView.as_view(), name="tenant-edit"),
]
