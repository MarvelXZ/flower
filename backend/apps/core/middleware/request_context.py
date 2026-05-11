"""Middleware that attaches request_id and correlation_id to every request.

Response headers:
- X-Request-ID
- X-Correlation-ID
"""

import uuid

from django.utils.deprecation import MiddlewareMixin


class RequestContextMiddleware(MiddlewareMixin):
    """Generate or propagate request and correlation IDs."""

    def process_request(self, request):
        request.request_id = str(uuid.uuid4())
        request.correlation_id = request.META.get(
            "HTTP_X_CORRELATION_ID",
            str(uuid.uuid4()),
        )

    def process_response(self, request, response):
        rid = getattr(request, "request_id", "")
        cid = getattr(request, "correlation_id", "")
        if rid:
            response["X-Request-ID"] = rid
        if cid:
            response["X-Correlation-ID"] = cid
        return response
