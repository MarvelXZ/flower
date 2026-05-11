import hashlib
import json
from dataclasses import dataclass

from django.db import transaction

from apps.provider_ops.models import B2BIdempotencyKey


class MissingIdempotencyKey(ValueError):
    """Raised when a mutating B2B endpoint has no idempotency key."""


class IdempotencyConflict(ValueError):
    """Raised when an idempotency key is reused with a different request body."""


@dataclass(frozen=True)
class IdempotencyResult:
    response_status: int
    response_body: dict
    cached: bool = False


def compute_request_hash(payload) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def execute_idempotent_request(
    *,
    key: str | None,
    endpoint: str,
    payload,
    handler,
) -> IdempotencyResult:
    """Run a write handler once for a given key/endpoint/request hash."""
    if not key:
        raise MissingIdempotencyKey("X-Idempotency-Key is required.")

    request_hash = compute_request_hash(payload)

    with transaction.atomic():
        existing = B2BIdempotencyKey.objects.filter(key=key, endpoint=endpoint).first()
        if existing:
            if existing.request_hash != request_hash:
                raise IdempotencyConflict("Idempotency key reused with a different payload.")
            return IdempotencyResult(
                response_status=existing.response_status,
                response_body=existing.response_body,
                cached=True,
            )

        response_status, response_body = handler()
        B2BIdempotencyKey.objects.create(
            key=key,
            endpoint=endpoint,
            request_hash=request_hash,
            response_status=response_status,
            response_body=response_body,
        )

    return IdempotencyResult(
        response_status=response_status,
        response_body=response_body,
        cached=False,
    )
