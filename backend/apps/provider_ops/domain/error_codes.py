"""Stable, machine-readable error codes for the provider/mobile API.

Mobile apps should key off ``code``, never ``message``.
"""

# --- Task ---
TASK_INVALID_TRANSITION = "task_invalid_transition"
TASK_NOT_FOUND = "task_not_found"
TASK_NOT_ASSIGNABLE = "task_not_assignable"

# --- SLA ---
SLA_ALREADY_BREACHED = "sla_already_breached"
SLA_NOT_FOUND = "sla_not_found"

# --- Notifications ---
NOTIFICATION_DELIVERY_FAILED = "notification_delivery_failed"
NOTIFICATION_NOT_FOUND = "notification_not_found"

# --- General API ---
VALIDATION_ERROR = "validation_error"
INVALID_FILTER_PARAM = "invalid_filter_param"
THROTTLED = "throttled"
UNAUTHORIZED = "unauthorized"
FORBIDDEN = "forbidden"
NOT_FOUND = "not_found"
CONFLICT = "conflict"
STALE_VERSION = "stale_version"
IDEMPOTENCY_REPLAY = "idempotency_replay"
INTERNAL_ERROR = "internal_error"
