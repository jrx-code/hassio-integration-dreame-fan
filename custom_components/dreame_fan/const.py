"""Constants for the Dreame Fan integration."""

from typing import Final

DOMAIN: Final = "dreame_fan"

# dreame.fan.u2519 is the Dreame Bladeless Fan MF10. It has no published MIoT
# spec; the property map was established by driving the fan from the Dreamehome
# app and watching which value moved. See docs/miot-properties.md.
MODEL_MF10: Final = "dreame.fan.u2519"
SUPPORTED_MODELS: Final = (MODEL_MF10,)

CONF_COUNTRY: Final = "country"
CONF_DID: Final = "did"

DEFAULT_COUNTRY: Final = "eu"
COUNTRIES: Final = ("eu", "de", "us", "cn")

UPDATE_INTERVAL_SECONDS: Final = 30

# The cloud's cached property view lags an acknowledged write. Changes made from
# the app appear within about 5 seconds, but writes issued here have taken up to
# 50. An accepted write is applied optimistically and reconciled by a later poll.
WRITE_RECONCILE_SECONDS: Final = 60

# --- confirmed properties -------------------------------------------------
# Each was established by changing exactly one control and observing the value.

PROP_POWER: Final = "2.1"          # 1 = running, 2 = off. Rejects writes.
PROP_MODE: Final = "2.3"           # see MODES
PROP_SPEED: Final = "2.4"          # 1-10; not writable while the fan is off
PROP_OSCILLATION: Final = "2.7"    # 0 / 1
PROP_BLADES: Final = "2.8"         # bitmask: 1 = left, 2 = right, 3 = both
PROP_TEMPERATURE: Final = "3.2"    # degC; 3.3 carries the same value
PROP_TEMPERATURE_ALT: Final = "3.3"
PROP_FILTER_DAYS: Final = "4.8"    # pre-filter days remaining
PROP_TIMER_HOURS: Final = "6.8"    # 0 = off
PROP_CHILD_LOCK: Final = "6.10"    # 0 / 1

POWER_ON: Final = 1
POWER_OFF: Final = 2

SPEED_MIN: Final = 1
SPEED_MAX: Final = 10

BLADE_LEFT: Final = 1
BLADE_RIGHT: Final = 2

# Mode values, left to right in the app's picker, which is also F1-F5 on the
# remote. Names are the app's own, not invented: Auto, Tryb nocny, Tryb
# naturalny, Tryb Mocny, Tryb niestandardowy.
MODE_AUTO: Final = 0        # F1
MODE_STRONG: Final = 1      # F4
MODE_NIGHT: Final = 2       # F2
MODE_CUSTOM: Final = 3      # F5
MODE_NATURAL: Final = 7     # F3

MODES: Final[dict[int, str]] = {
    MODE_AUTO: "auto",
    MODE_NIGHT: "night",
    MODE_NATURAL: "natural",
    MODE_STRONG: "strong",
    MODE_CUSTOM: "custom",
}
MODE_VALUES: Final[dict[str, int]] = {name: value for value, name in MODES.items()}

CONFIRMED_PROPERTIES: Final[dict[str, str]] = {
    PROP_POWER: "power",
    PROP_MODE: "mode",
    PROP_SPEED: "speed",
    PROP_OSCILLATION: "oscillation",
    PROP_BLADES: "blades",
    PROP_TEMPERATURE: "temperature",
    PROP_TEMPERATURE_ALT: "temperature_secondary",
    PROP_FILTER_DAYS: "filter_days",
    PROP_TIMER_HOURS: "timer_hours",
    PROP_CHILD_LOCK: "child_lock",
}

# Writes verified accepted and read back, then restored.
KNOWN_WRITABLE: Final = (
    PROP_MODE,
    PROP_SPEED,
    PROP_OSCILLATION,
    PROP_BLADES,
    PROP_TIMER_HOURS,
    PROP_CHILD_LOCK,
)

# Every property the device answers for, as "<siid>.<piid>". The endpoint does
# not enumerate, so this list has to be explicit. Discovered by scanning
# siid 1-15 x piid 1-30; everything outside this set returned nothing.
PROPERTY_KEYS: Final = (
    "1.8",
    "2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8", "2.9",
    "2.10", "2.11", "2.12", "2.15",
    "3.2", "3.3",
    "4.1", "4.2", "4.7", "4.8",
    "6.4", "6.7", "6.8", "6.10", "6.11", "6.12", "6.17", "6.30",
)

SERVICE_SET_PROPERTY: Final = "set_property"
ATTR_PROPERTY: Final = "property"
ATTR_VALUE: Final = "value"
