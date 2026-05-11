"""Mapping from alert rule codes and severity to provider task payloads."""

from dataclasses import dataclass

from apps.provider_ops.domain.enums import ProviderTaskPriority, ProviderTaskType


@dataclass(frozen=True)
class TaskPayload:
    task_type: str
    priority: str
    title: str
    description: str


_RULE_TO_TASK_TYPE: dict[str, str] = {
    "soil_moisture_low": ProviderTaskType.WATERING,
    "soil_moisture_high": ProviderTaskType.INSPECTION,
    "temperature_low": ProviderTaskType.INSPECTION,
    "temperature_high": ProviderTaskType.INSPECTION,
    "air_humidity_low": ProviderTaskType.INSPECTION,
    "air_humidity_high": ProviderTaskType.INSPECTION,
    "battery_low": ProviderTaskType.DEVICE_CHECK,
    "device_offline": ProviderTaskType.DEVICE_CHECK,
}


_SEVERITY_TO_PRIORITY: dict[str, str] = {
    "critical": ProviderTaskPriority.URGENT,
    "warning": ProviderTaskPriority.HIGH,
    "info": ProviderTaskPriority.NORMAL,
}


def map_alert_to_task_payload(*, rule_code: str, severity: str, title: str, message: str) -> TaskPayload:
    """Map an alert's rule code and severity to a task type and priority."""
    task_type = _RULE_TO_TASK_TYPE.get(rule_code, ProviderTaskType.MAINTENANCE)
    priority = _SEVERITY_TO_PRIORITY.get(severity, ProviderTaskPriority.NORMAL)
    return TaskPayload(
        task_type=task_type,
        priority=priority,
        title=title,
        description=message,
    )


def build_task_key(*, source_owner_tenant_id: str, external_alert_id: str, task_type: str) -> str:
    """Build a deterministic task key for idempotency."""
    return f"{source_owner_tenant_id}:{external_alert_id}:{task_type}"
