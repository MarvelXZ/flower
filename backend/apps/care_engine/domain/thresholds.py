"""Default threshold values for care rule evaluation.

These constants are the system defaults.  Future phases will allow
per-plant overrides via ``PlantCareProfile``.
"""

# Soil moisture (percentage 0–100)
SOIL_MOISTURE_MIN = 20.0
SOIL_MOISTURE_MAX = 80.0

# Temperature (Celsius)
TEMPERATURE_MIN = 5.0
TEMPERATURE_MAX = 40.0

# Air humidity (percentage 0–100)
AIR_HUMIDITY_MIN = 30.0
AIR_HUMIDITY_MAX = 90.0

# Battery (percentage 0–100)
BATTERY_MIN = 15.0
