import hashlib
import hmac
import json
import time
from dataclasses import replace


HMAC_TIMESTAMP_HEADER = "X-B2B-Timestamp"
HMAC_SIGNATURE_HEADER = "X-B2B-Signature"
HMAC_KEY_ID_HEADER = "X-B2B-Key-Id"
IDEMPOTENCY_KEY_HEADER = "X-Idempotency-Key"


class HMACVerificationError(ValueError):
    """Base error for inbound B2B HMAC verification failures."""


class MissingHMACHeader(HMACVerificationError):
    """Raised when a required HMAC header is absent."""


class InvalidHMACTimestamp(HMACVerificationError):
    """Raised when an HMAC timestamp is malformed or outside the allowed skew."""


class InvalidHMACSignature(HMACVerificationError):
    """Raised when an HMAC signature does not match the request."""


def serialize_json_body(payload: dict) -> bytes:
    """Serialize JSON deterministically so signed bytes match sent bytes."""
    return json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sha256_hex_body(body_bytes: bytes) -> str:
    return hashlib.sha256(body_bytes or b"").hexdigest()


def build_canonical_string(
    *,
    method: str,
    path: str,
    timestamp: str,
    idempotency_key: str,
    body_sha256: str,
) -> str:
    return "\n".join(
        [
            method.upper(),
            path,
            str(timestamp),
            idempotency_key,
            body_sha256,
        ]
    )


def sign_canonical_string(*, canonical_string: str, shared_secret: str) -> str:
    return hmac.new(
        shared_secret.encode("utf-8"),
        canonical_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_hmac_headers(
    *,
    method: str,
    path: str,
    body_bytes: bytes,
    idempotency_key: str,
    key_id: str,
    shared_secret: str,
    timestamp: str | int | None = None,
) -> dict:
    timestamp_value = str(timestamp if timestamp is not None else int(time.time()))
    body_sha256 = sha256_hex_body(body_bytes)
    canonical_string = build_canonical_string(
        method=method,
        path=path,
        timestamp=timestamp_value,
        idempotency_key=idempotency_key,
        body_sha256=body_sha256,
    )
    signature = sign_canonical_string(
        canonical_string=canonical_string,
        shared_secret=shared_secret,
    )
    return {
        HMAC_TIMESTAMP_HEADER: timestamp_value,
        HMAC_SIGNATURE_HEADER: signature,
        HMAC_KEY_ID_HEADER: key_id,
        IDEMPOTENCY_KEY_HEADER: idempotency_key,
    }


def sign_provider_request(
    request,
    *,
    key_id: str,
    shared_secret: str,
    timestamp: str | int | None = None,
):
    """Return a copy of a provider request with deterministic body bytes and HMAC headers."""
    body_bytes = serialize_json_body(request.payload)
    headers = {
        **request.headers,
        **build_hmac_headers(
            method=request.method,
            path=request.endpoint,
            body_bytes=body_bytes,
            idempotency_key=request.idempotency_key,
            key_id=key_id,
            shared_secret=shared_secret,
            timestamp=timestamp,
        ),
        "Content-Type": "application/json",
    }
    return replace(request, headers=headers, body_bytes=body_bytes)


def verify_hmac_signature(
    *,
    method: str,
    path: str,
    body_bytes: bytes,
    idempotency_key: str | None,
    key_id: str | None,
    timestamp: str | None,
    signature: str | None,
    expected_key_id: str,
    shared_secret: str,
    max_skew_seconds: int,
    now: int | None = None,
) -> None:
    if not all([idempotency_key, key_id, timestamp, signature]):
        raise MissingHMACHeader("Missing required HMAC authentication headers.")

    try:
        timestamp_seconds = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise InvalidHMACTimestamp("Invalid HMAC timestamp.") from exc

    current_time = int(time.time()) if now is None else int(now)
    if abs(current_time - timestamp_seconds) > max_skew_seconds:
        raise InvalidHMACTimestamp("Invalid HMAC timestamp.")

    if not hmac.compare_digest(str(key_id), str(expected_key_id)):
        raise InvalidHMACSignature("Invalid HMAC signature.")

    expected_headers = build_hmac_headers(
        method=method,
        path=path,
        body_bytes=body_bytes,
        idempotency_key=str(idempotency_key),
        key_id=str(key_id),
        shared_secret=shared_secret,
        timestamp=str(timestamp),
    )
    expected_signature = expected_headers[HMAC_SIGNATURE_HEADER]
    if not hmac.compare_digest(str(signature), expected_signature):
        raise InvalidHMACSignature("Invalid HMAC signature.")
