"""Custom API exceptions with stable error codes."""

from rest_framework import status
from rest_framework.exceptions import APIException


class TaskInvalidTransition(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Task cannot transition to the requested status."
    default_code = "task_invalid_transition"


class TaskNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Task not found."
    default_code = "task_not_found"


class StaleVersion(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource has been modified since last read."
    default_code = "stale_version"


class SLAAlreadyBreached(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "SLA has already been breached."
    default_code = "sla_already_breached"


class IdempotencyReplay(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Idempotency key replay detected with different payload."
    default_code = "idempotency_replay"
