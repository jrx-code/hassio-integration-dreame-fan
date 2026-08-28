"""Constants for the Dreame Fan integration."""

from typing import Final

DOMAIN: Final = "dreame_fan"

# dreame.fan.u2519 is the Dreame Bladeless Fan MF10. It has no published MIoT
# spec, so the property list below was discovered by scanning the cloud API;
# see docs/miot-properties.md.
MODEL_MF10: Final = "dreame.fan.u2519"
SUPPORTED_MODELS: Final = (MODEL_MF10,)

CONF_COUNTRY: Final = "country"
CONF_DID: Final = "did"

DEFAULT_COUNTRY: Final = "eu"
COUNTRIES: Final = ("eu", "de", "us", "cn")

UPDATE_INTERVAL_SECONDS: Final = 30

# The cloud's cached property view lags an acknowledged write: measured between
# 35 and 50 seconds on 2.4. Reading back sooner returns the old value, so an
# accepted write is applied optimistically and reconciled by a later poll.
WRITE_RECONCILE_SECONDS: Final = 60

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

# Properties whose meaning has been established by observation go here, and get
# a real entity instead of a raw diagnostic sensor. Nothing has been confirmed
# yet: a snapshot of numbers is not evidence of what a number is.
CONFIRMED_PROPERTIES: Final[dict[str, str]] = {}

# Writes that the device accepted, verified by reading the value back.
KNOWN_WRITABLE: Final = ("2.4",)

SERVICE_SET_PROPERTY: Final = "set_property"
ATTR_PROPERTY: Final = "property"
ATTR_VALUE: Final = "value"
