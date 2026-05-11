"""Standardized mobile API response envelope.

All provider dashboard list endpoints return:

{
    "results": [...],
    "count": 123,
    "next": "...",
    "previous": "...",
    "meta": {
        "generated_at": "...",
        "compact": true
    }
}
"""


from django.utils import timezone
from rest_framework.response import Response


def mobile_list_response(paginator, queryset, serializer_class, request, *, extra_meta: dict | None = None) -> Response:
    """Build a standardised mobile list response.

    Handles pagination, serialization, and metadata in one call.
    """
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = serializer_class(page, many=True, context={"request": request})
        data = paginator.get_paginated_response(serializer.data).data
    else:
        serializer = serializer_class(queryset, many=True, context={"request": request})
        data = {"results": serializer.data, "count": len(serializer.data), "next": None, "previous": None}

    meta = {
        "generated_at": timezone.now().isoformat(),
        "compact": True,
    }
    if extra_meta:
        meta.update(extra_meta)
    data["meta"] = meta

    return Response(data)
