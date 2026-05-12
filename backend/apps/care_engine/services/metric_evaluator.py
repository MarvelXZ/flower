"""Generic metric evaluator service.

Evaluates a (device, metric_key, value) tuple against all enabled rules
for that metric.  Handles cooldown, dedup, and alert lifecycle.

This is the bridge between the Device Event Bus and the Rule Engine:
- Sensor readings flow through ``evaluate_sensor_reading``
- Device events (offline, heartbeat) flow through ``evaluate_device_metric``
"""

import logging
from datetime import timedelta

from django.utils import timezone

from apps.care_engine.models import Rule as RuleModel
from apps.notifications.domain.enums import AlertSeverity, AlertSourceType, AlertStatus
from apps.notifications.models import Alert
from apps.notifications.services.alert_service import open_or_update_alert, resolve_alert

logger = logging.getLogger("flower.rules.evaluator")


def evaluate_metric(
    *,
    device_identifier: str,
    metric_key: str,
    value: float,
    source_type: str = AlertSourceType.SENSOR_READING,
    source_id: str = "",
    device=None,
    sensor_reading=None,
) -> list:
    """Evaluate all enabled rules for a metric against a value.

    For each matching rule:
    1. Check if the value triggers the rule condition.
    2. If triggered, check cooldown — skip if within cooldown window.
    3. Open or update the alert via ``open_or_update_alert``.

    Returns the list of alerts created or updated.
    """
    rules = RuleModel.objects.filter(metric_key=metric_key, enabled=True)
    results = []

    for rule in rules:
        if not rule.evaluate(value):
            # Rule not triggered — check if existing alert should be resolved
            _maybe_resolve_alert(rule=rule, device_identifier=device_identifier)
            continue

        if _is_in_cooldown(rule=rule, device_identifier=device_identifier):
            logger.debug(
                "rule_in_cooldown",
                extra={
                    "rule_id": rule.pk,
                    "metric_key": metric_key,
                    "device": device_identifier,
                },
            )
            continue

        alert_key = rule.alert_key(device_identifier=device_identifier)
        alert = open_or_update_alert(
            alert_key=alert_key,
            source_type=source_type,
            source_id=source_id,
            severity=rule.severity,
            title=f"{rule.name}",
            message=f"{rule.metric_key} is {value:.1f} ({rule.operator} {rule.threshold_value}).",
            device=device,
            sensor_reading=sensor_reading,
            rule_code=rule.metric_key,
            metadata={
                "rule_id": rule.pk,
                "metric_key": metric_key,
                "value": value,
                "operator": rule.operator,
                "threshold": rule.threshold_value,
            },
        )
        results.append(alert)

    return results


def evaluate_sensor_reading(sensor_reading) -> list:
    """Evaluate all metric channels on a sensor reading."""
    results = []

    device = sensor_reading.device
    device_id = str(device.pk) if device else "unknown"

    metrics = {
        "soil_moisture": sensor_reading.soil_moisture,
        "temperature": sensor_reading.temperature,
        "air_humidity": sensor_reading.air_humidity,
        "battery_level": sensor_reading.battery_level,
        "light_level": sensor_reading.light_level,
    }

    for metric_key, value in metrics.items():
        if value is None:
            continue
        alerts = evaluate_metric(
            device_identifier=device_id,
            metric_key=metric_key,
            value=float(value),
            source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk),
            device=device,
            sensor_reading=sensor_reading,
        )
        results.extend(alerts)

    return results


def evaluate_device_metric(
    *,
    device_identifier: str,
    metric_key: str,
    value: float,
    device=None,
    source_type: str = AlertSourceType.DEVICE,
    source_id: str = "",
) -> list:
    """Evaluate a standalone metric from a device event (e.g. heartbeat, offline)."""
    return evaluate_metric(
        device_identifier=device_identifier,
        metric_key=metric_key,
        value=value,
        source_type=source_type,
        source_id=source_id,
        device=device,
    )


# ---------------------------------------------------------------------------
# Cooldown logic
# ---------------------------------------------------------------------------


def _is_in_cooldown(*, rule, device_identifier: str) -> bool:
    """Return True if the rule is in cooldown for this device."""
    if rule.cooldown_seconds <= 0:
        return False

    alert_key = rule.alert_key(device_identifier=device_identifier)
    recent = Alert.objects.filter(
        alert_key=alert_key,
        status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
    ).order_by("-last_seen_at").first()

    if recent is None:
        return False

    cutoff = timezone.now() - timedelta(seconds=rule.cooldown_seconds)
    return recent.last_seen_at > cutoff


def _maybe_resolve_alert(*, rule, device_identifier: str) -> None:
    """If there's an open alert for this rule+device and the value is
    back to normal, resolve it.

    This is called when a sensor reading is within normal range.
    """
    alert_key = rule.alert_key(device_identifier=device_identifier)
    open_alert = Alert.objects.filter(
        alert_key=alert_key,
        status__in={AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED},
    ).first()

    if open_alert:
        resolve_alert(alert=open_alert)
