
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenancy.api.serializers import TenantCreateSerializer, TenantListSerializer
from apps.tenancy.selectors import active_tenants
from apps.tenancy.services import create_tenant


class TenantListCreateView(APIView):
    """List tenants and create a new company tenant.

    This is the first slice of tenant onboarding. Follow-up steps should attach
    billing, create an initial admin user, and optionally create provider
    engagement records.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        tenants = active_tenants().prefetch_related("domains").order_by("name")
        serializer = TenantListSerializer(tenants, many=True)
        return Response({"results": serializer.data})

    def post(self, request):
        serializer = TenantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        tenant = create_tenant(
            name=data["name"],
            slug=data["slug"],
            schema_name=data["schema_name"],
            domain=data["domain"],
            kind=data["kind"],
        )

        return Response(TenantListSerializer(tenant).data, status=status.HTTP_201_CREATED)
