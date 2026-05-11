"""Tests for API contract hardening (Phase 16A)."""

from types import SimpleNamespace

from django.http import HttpRequest
from rest_framework.exceptions import ValidationError

from apps.provider_ops.api.concurrency import check_version, compute_etag
from apps.provider_ops.api.errors import (
    _build_error_payload,
    _map_exception_to_code,
    flower_exception_handler,
)
from apps.provider_ops.api.response_meta import build_meta
from apps.provider_ops.domain import error_codes
from apps.provider_ops.domain.error_codes import VALIDATION_ERROR


# ============================================================================
# 1. Error envelope
# ============================================================================


def test_error_payload_has_required_fields():
    payload = _build_error_payload(
        code="test_error",
        message="Something went wrong.",
        request_id="req-1",
        correlation_id="corr-1",
    )
    assert "error" in payload
    err = payload["error"]
    assert err["code"] == "test_error"
    assert err["message"] == "Something went wrong."
    assert err["request_id"] == "req-1"
    assert err["correlation_id"] == "corr-1"
    assert "timestamp" in err


def test_error_payload_has_details():
    payload = _build_error_payload(
        code="validation_error", message="Invalid input.",
        details={"field": ["This field is required."]},
    )
    assert payload["error"]["details"]["field"] == ["This field is required."]


# ============================================================================
# 2. Exception mapping
# ============================================================================


def test_validation_error_maps_correctly():
    exc = ValidationError(detail={"name": ["Required."]})
    code = _map_exception_to_code(exc)
    assert code == VALIDATION_ERROR


def test_unknown_exception_maps_to_internal():
    exc = RuntimeError("boom")
    # _map_exception_to_code expects BaseAPIException
    # So we test the fallback for non-APIException
    from rest_framework.exceptions import APIException
    class CustomAPIError(APIException):
        status_code = 500
        default_detail = "Custom error"
    exc = CustomAPIError()
    code = _map_exception_to_code(exc)
    assert code == error_codes.INTERNAL_ERROR


# ============================================================================
# 3. Exception handler
# ============================================================================


def test_exception_handler_returns_envelope():
    request = HttpRequest()
    request.request_id = "req-1"
    request.correlation_id = "corr-1"

    exc = ValidationError(detail={"name": ["Required."]})
    context = {"request": request, "view": None}
    response = flower_exception_handler(exc, context)

    assert response is not None
    assert "error" in response.data
    assert response.data["error"]["code"] == VALIDATION_ERROR
    assert response.data["error"]["request_id"] == "req-1"


# ============================================================================
# 4. Concurrency
# ============================================================================


def test_check_version_matches():
    obj = SimpleNamespace(version=3)
    assert check_version(obj=obj, expected_version=3) is True


def test_check_version_mismatch():
    obj = SimpleNamespace(version=3)
    assert check_version(obj=obj, expected_version=2) is False


def test_check_version_none_skips_check():
    obj = SimpleNamespace(version=3)
    assert check_version(obj=obj, expected_version=None) is True


def test_compute_etag_stable():
    obj1 = SimpleNamespace(__class__=SimpleNamespace(__name__="Task"), pk=1, version=1, updated_at=None)
    obj2 = SimpleNamespace(__class__=SimpleNamespace(__name__="Task"), pk=1, version=1, updated_at=None)
    assert compute_etag(obj1) == compute_etag(obj2)


# ============================================================================
# 5. Response meta
# ============================================================================


def test_build_meta_has_required_fields():
    request = HttpRequest()
    request.request_id = "req-1"
    request.correlation_id = "corr-1"
    meta = build_meta(request)
    assert meta["request_id"] == "req-1"
    assert meta["correlation_id"] == "corr-1"
    assert meta["api_version"] == "v1"
    assert "generated_at" in meta


# ============================================================================
# 6. Error codes module
# ============================================================================


def test_error_codes_are_stable():
    assert error_codes.TASK_INVALID_TRANSITION == "task_invalid_transition"
    assert error_codes.VALIDATION_ERROR == "validation_error"
    assert error_codes.STALE_VERSION == "stale_version"
    assert error_codes.THROTTLED == "throttled"
