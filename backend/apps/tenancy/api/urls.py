
from django.urls import path

from apps.tenancy.api.views import TenantListCreateView

app_name = "tenancy"

urlpatterns = [
    path("tenants/", TenantListCreateView.as_view(), name="tenant-list-create"),
]
