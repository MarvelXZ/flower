"""Rule evaluation engine for sensor readings.

Evaluates incoming ``SensorReading`` data against default thresholds and
creates or updates ``Alert`` records via ``alert_service``.
"""

from apps.care_engine.domain.rule_codes import RuleCode
from apps.care_engine.domain.thresholds import (
    AIR_HUMIDITY_MAX,
    AIR_HUMIDITY_MIN,
    BATTERY_MIN,
    SOIL_MOISTURE_MAX,
    SOIL_MOISTURE_MIN,
    TEMPERATURE_MAX,
    TEMPERATURE_MIN,
)
from apps.notifications.domain.enums import AlertSeverity, AlertSourceType
from apps.notifications.services.alert_service import open_or_update_alert


def _build_alert_key(*, rule_code: str, sensor_reading) -> str:
    """Build a deterministic alert key for a rule + device combination."""
    device_id = sensor_reading.device_id
    return f"{rule_code}:device_{device_id}"


def _device_has_plant(sensor_reading):
    """Return the plant associated with the sensor's device, if any."""
    device = sensor_reading.device
    return getattr(device, "plant", None)


# ---------------------------------------------------------------------------
# Single-rule evaluators
# ---------------------------------------------------------------------------


def evaluate_soil_moisture(sensor_reading, *, plant=None) -> list | None:
    """Evaluate soil moisture against thresholds. Returns ``None`` if normal."""
    value = sensor_reading.soil_moisture
    if value is None:
        return None

    alert_key = _build_alert_key(rule_code=RuleCode.SOIL_MOISTURE_LOW, sensor_reading=sensor_reading)
    results = []

    if value < SOIL_MOISTURE_MIN:
        alert = open_or_update_alert(
            alert_key=alert_key,
            source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk),
            severity=AlertSeverity.CRITICAL,
            title="Soil moisture critically low",
            message=f"Soil moisture is {value:.1f}% (min {SOIL_MOISTURE_MIN:.0f}%).",
            plant=plant,
            device=sensor_reading.device,
            sensor_reading=sensor_reading,
            rule_code=RuleCode.SOIL_MOISTURE_LOW,
            metadata={"value": value, "threshold_min": SOIL_MOISTURE_MIN},
        )
        results.append(alert)
    elif value > SOIL_MOISTURE_MAX:
        alert_key_high = _build_alert_key(rule_code=RuleCode.SOIL_MOISTURE_HIGH, sensor_reading=sensor_reading)
        alert = open_or_update_alert(
            alert_key=alert_key_high,
            source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk),
            severity=AlertSeverity.WARNING,
            title="Soil moisture too high",
            message=f"Soil moisture is {value:.1f}% (max {SOIL_MOISTURE_MAX:.0f}%).",
            plant=plant,
            device=sensor_reading.device,
            sensor_reading=sensor_reading,
            rule_code=RuleCode.SOIL_MOISTURE_HIGH,
            metadata={"value": value, "threshold_max": SOIL_MOISTURE_MAX},
        )
        results.append(alert)

    return results or None


def evaluate_temperature(sensor_reading, *, plant=None) -> list | None:
    """Evaluate temperature against thresholds."""
    value = sensor_reading.temperature
    if value is None:
        return None

    results = []
    if value < TEMPERATURE_MIN:
        ak = _build_alert_key(rule_code=RuleCode.TEMPERATURE_LOW, sensor_reading=sensor_reading)
        alert = open_or_update_alert(
            alert_key=ak, source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk), severity=AlertSeverity.CRITICAL,
            title="Temperature critically low",
            message=f"Temperature is {value:.1f}°C (min {TEMPERATURE_MIN:.0f}°C).",
            plant=plant, device=sensor_reading.device, sensor_reading=sensor_reading,
            rule_code=RuleCode.TEMPERATURE_LOW,
            metadata={"value": value, "threshold_min": TEMPERATURE_MIN},
        )
        results.append(alert)
    elif value > TEMPERATURE_MAX:
        ak = _build_alert_key(rule_code=RuleCode.TEMPERATURE_HIGH, sensor_reading=sensor_reading)
        alert = open_or_update_alert(
            alert_key=ak, source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk), severity=AlertSeverity.CRITICAL,
            title="Temperature too high",
            message=f"Temperature is {value:.1f}°C (max {TEMPERATURE_MAX:.0f}°C).",
            plant=plant, device=sensor_reading.device, sensor_reading=sensor_reading,
            rule_code=RuleCode.TEMPERATURE_HIGH,
            metadata={"value": value, "threshold_max": TEMPERATURE_MAX},
        )
        results.append(alert)

    return results or None


def evaluate_air_humidity(sensor_reading, *, plant=None) -> list | None:
    """Evaluate air humidity against thresholds."""
    value = sensor_reading.air_humidity
    if value is None:
        return None

    results = []
    if value < AIR_HUMIDITY_MIN:
        ak = _build_alert_key(rule_code=RuleCode.AIR_HUMIDITY_LOW, sensor_reading=sensor_reading)
        alert = open_or_update_alert(
            alert_key=ak, source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk), severity=AlertSeverity.WARNING,
            title="Air humidity low",
            message=f"Air humidity is {value:.1f}% (min {AIR_HUMIDITY_MIN:.0f}%).",
            plant=plant, device=sensor_reading.device, sensor_reading=sensor_reading,
            rule_code=RuleCode.AIR_HUMIDITY_LOW,
            metadata={"value": value, "threshold_min": AIR_HUMIDITY_MIN},
        )
        results.append(alert)
    elif value > AIR_HUMIDITY_MAX:
        ak = _build_alert_key(rule_code=RuleCode.AIR_HUMIDITY_HIGH, sensor_reading=sensor_reading)
        alert = open_or_update_alert(
            alert_key=ak, source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk), severity=AlertSeverity.WARNING,
            title="Air humidity high",
            message=f"Air humidity is {value:.1f}% (max {AIR_HUMIDITY_MAX:.0f}%).",
            plant=plant, device=sensor_reading.device, sensor_reading=sensor_reading,
            rule_code=RuleCode.AIR_HUMIDITY_HIGH,
            metadata={"value": value, "threshold_max": AIR_HUMIDITY_MAX},
        )
        results.append(alert)

    return results or None


def evaluate_battery(sensor_reading, *, plant=None) -> list | None:
    """Evaluate battery level against threshold."""
    value = sensor_reading.battery_level
    if value is None:
        return None

    if value < BATTERY_MIN:
        ak = _build_alert_key(rule_code=RuleCode.BATTERY_LOW, sensor_reading=sensor_reading)
        alert = open_or_update_alert(
            alert_key=ak, source_type=AlertSourceType.SENSOR_READING,
            source_id=str(sensor_reading.pk), severity=AlertSeverity.WARNING,
            title="Battery level low",
            message=f"Battery is {value:.1f}% (min {BATTERY_MIN:.0f}%).",
            plant=plant, device=sensor_reading.device, sensor_reading=sensor_reading,
            rule_code=RuleCode.BATTERY_LOW,
            metadata={"value": value, "threshold_min": BATTERY_MIN},
        )
        return [alert]

    return None


# ---------------------------------------------------------------------------
# Top-level evaluation
# ---------------------------------------------------------------------------


def evaluate_sensor_reading(sensor_reading) -> list:
    """Evaluate all applicable rules for a ``SensorReading``.

    Returns a flat list of all ``Alert`` instances that were created or
    updated during evaluation.
    """
    plant = _device_has_plant(sensor_reading)
    alerts = []

    for evaluator in (
        evaluate_soil_moisture,
        evaluate_temperature,
        evaluate_air_humidity,
        evaluate_battery,
    ):
        result = evaluator(sensor_reading, plant=plant)
        if result:
            alerts.extend(result)

    return alerts
