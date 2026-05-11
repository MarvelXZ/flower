"""Unit tests for rule evaluation engine (Phase 11)."""

from types import SimpleNamespace


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
from apps.care_engine.services.rule_evaluation_service import (
    _build_alert_key,
    evaluate_air_humidity,
    evaluate_battery,
    evaluate_sensor_reading,
    evaluate_soil_moisture,
    evaluate_temperature,
)


# ============================================================================
# Helpers
# ============================================================================

def _make_reading(**overrides):
    device = SimpleNamespace(
        pk=1,
        device_id=1,
        plant=None,
    )
    defaults = {
        "pk": 1,
        "device": device,
        "device_id": 1,
        "soil_moisture": 50.0,
        "temperature": 22.0,
        "air_humidity": 60.0,
        "battery_level": 80.0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_reading_with_plant(**overrides):
    plant = SimpleNamespace(pk=1)
    device = SimpleNamespace(
        pk=1,
        device_id=1,
        plant=plant,
    )
    defaults = {
        "pk": 1,
        "device": device,
        "device_id": 1,
        "soil_moisture": 50.0,
        "temperature": 22.0,
        "air_humidity": 60.0,
        "battery_level": 80.0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ============================================================================
# _build_alert_key
# ============================================================================


def test_build_alert_key():
    reading = _make_reading()
    key = _build_alert_key(rule_code="soil_moisture_low", sensor_reading=reading)
    assert key == "soil_moisture_low:device_1"


# ============================================================================
# evaluate_soil_moisture
# ============================================================================


def test_soil_moisture_low_creates_alert(monkeypatch):
    reading = _make_reading(soil_moisture=SOIL_MOISTURE_MIN - 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=1, rule_code=RuleCode.SOIL_MOISTURE_LOW),
    )
    result = evaluate_soil_moisture(reading)
    assert result is not None
    assert len(result) == 1


def test_soil_moisture_high_creates_alert(monkeypatch):
    reading = _make_reading(soil_moisture=SOIL_MOISTURE_MAX + 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=2, rule_code=kw.get("rule_code")),
    )
    result = evaluate_soil_moisture(reading)
    assert result is not None
    assert len(result) == 1


def test_soil_moisture_normal_returns_none(monkeypatch):
    reading = _make_reading(soil_moisture=50.0)
    result = evaluate_soil_moisture(reading)
    assert result is None


def test_soil_moisture_none_returns_none():
    reading = _make_reading(soil_moisture=None)
    result = evaluate_soil_moisture(reading)
    assert result is None


# ============================================================================
# evaluate_temperature
# ============================================================================


def test_temperature_low_creates_alert(monkeypatch):
    reading = _make_reading(temperature=TEMPERATURE_MIN - 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=3, rule_code=kw.get("rule_code")),
    )
    result = evaluate_temperature(reading)
    assert result is not None


def test_temperature_high_creates_alert(monkeypatch):
    reading = _make_reading(temperature=TEMPERATURE_MAX + 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=4, rule_code=kw.get("rule_code")),
    )
    result = evaluate_temperature(reading)
    assert result is not None


def test_temperature_normal_returns_none():
    reading = _make_reading(temperature=22.0)
    result = evaluate_temperature(reading)
    assert result is None


# ============================================================================
# evaluate_air_humidity
# ============================================================================


def test_air_humidity_low_creates_alert(monkeypatch):
    reading = _make_reading(air_humidity=AIR_HUMIDITY_MIN - 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=5, rule_code=kw.get("rule_code")),
    )
    result = evaluate_air_humidity(reading)
    assert result is not None


def test_air_humidity_high_creates_alert(monkeypatch):
    reading = _make_reading(air_humidity=AIR_HUMIDITY_MAX + 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=6, rule_code=kw.get("rule_code")),
    )
    result = evaluate_air_humidity(reading)
    assert result is not None


def test_air_humidity_normal_returns_none():
    reading = _make_reading(air_humidity=60.0)
    result = evaluate_air_humidity(reading)
    assert result is None


# ============================================================================
# evaluate_battery
# ============================================================================


def test_battery_low_creates_alert(monkeypatch):
    reading = _make_reading(battery_level=BATTERY_MIN - 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=7, rule_code=kw.get("rule_code")),
    )
    result = evaluate_battery(reading)
    assert result is not None


def test_battery_normal_returns_none():
    reading = _make_reading(battery_level=80.0)
    result = evaluate_battery(reading)
    assert result is None


def test_battery_none_returns_none():
    reading = _make_reading(battery_level=None)
    result = evaluate_battery(reading)
    assert result is None


# ============================================================================
# evaluate_sensor_reading (top-level)
# ============================================================================


def test_evaluate_sensor_reading_multiple_alerts(monkeypatch):
    reading = _make_reading(
        soil_moisture=SOIL_MOISTURE_MIN - 5,
        temperature=TEMPERATURE_MAX + 5,
        air_humidity=AIR_HUMIDITY_MIN - 5,
        battery_level=BATTERY_MIN - 5,
    )
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=1, rule_code=kw.get("rule_code")),
    )
    alerts = evaluate_sensor_reading(reading)
    assert len(alerts) >= 3  # At least soil moisture + temp + battery


def test_evaluate_sensor_reading_normal_no_alerts(monkeypatch):
    reading = _make_reading(
        soil_moisture=50.0,
        temperature=22.0,
        air_humidity=60.0,
        battery_level=80.0,
    )
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=1, rule_code=kw.get("rule_code")),
    )
    alerts = evaluate_sensor_reading(reading)
    assert len(alerts) == 0


def test_evaluate_sensor_reading_with_plant(monkeypatch):
    reader = _make_reading_with_plant(soil_moisture=SOIL_MOISTURE_MIN - 5)
    monkeypatch.setattr(
        "apps.care_engine.services.rule_evaluation_service.open_or_update_alert",
        lambda **kw: SimpleNamespace(pk=1, rule_code=kw.get("rule_code")),
    )
    alerts = evaluate_sensor_reading(reader)
    assert len(alerts) >= 1
