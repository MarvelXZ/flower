from types import SimpleNamespace

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.tenancy.api.serializers import TenantCreateSerializer
from apps.tenancy.api.views import TenantListCreateView
from apps.tenancy.domain.enums import TenantKind


def test_tenant_create_serializer_rejects_invalid_schema_name(db):
    serializer = TenantCreateSerializer(
        data={
            "name": "Acme Flowers",
            "slug": "acme-flowers",
            "schema_name": "Acme Flowers",
            "domain": "acme.localhost",
            "kind": TenantKind.OWNER,
        }
    )

    assert not serializer.is_valid()
    assert "schema_name" in serializer.errors


def test_tenant_create_serializer_normalizes_domain(db):
    serializer = TenantCreateSerializer(
        data={
            "name": "Acme Flowers",
            "slug": "acme-flowers",
            "schema_name": "acme_flowers",
            "domain": "ACME.localhost",
            "kind": TenantKind.OWNER,
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["domain"] == "acme.localhost"


def test_tenant_create_view_delegates_to_service(db, monkeypatch):
    calls = {}

    def fake_create_tenant(**kwargs):
        calls.update(kwargs)
        return SimpleNamespace(
            id=1,
            name=kwargs["name"],
            slug=kwargs["slug"],
            schema_name=kwargs["schema_name"],
            kind=kwargs["kind"],
            is_active=True,
            created_at=None,
            updated_at=None,
            domains=SimpleNamespace(
                filter=lambda **filters: SimpleNamespace(first=lambda: SimpleNamespace(domain=kwargs["domain"]))
            ),
        )

    monkeypatch.setattr("apps.tenancy.api.views.create_tenant", fake_create_tenant)

    request = APIRequestFactory().post(
        reverse("tenancy:tenant-list-create"),
        {
            "name": "Acme Flowers",
            "slug": "acme-flowers",
            "schema_name": "acme_flowers",
            "domain": "acme.localhost",
            "kind": TenantKind.OWNER,
        },
        format="json",
    )
    force_authenticate(request, user=SimpleNamespace(is_staff=True, is_active=True))

    response = TenantListCreateView.as_view()(request)

    assert response.status_code == status.HTTP_201_CREATED
    assert calls == {
        "name": "Acme Flowers",
        "slug": "acme-flowers",
        "schema_name": "acme_flowers",
        "domain": "acme.localhost",
        "kind": TenantKind.OWNER,
    }
    assert response.data["primary_domain"] == "acme.localhost"
