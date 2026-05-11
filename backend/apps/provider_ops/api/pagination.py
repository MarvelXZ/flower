"""Pagination for the provider dashboard API."""

from rest_framework.pagination import LimitOffsetPagination


class ProviderDashboardPagination(LimitOffsetPagination):
    """Mobile-friendly pagination with sensible defaults."""

    default_limit = 20
    max_limit = 100
    limit_query_param = "limit"
    offset_query_param = "offset"
