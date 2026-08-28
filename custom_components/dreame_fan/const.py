"""Constants for the Dreame Fan integration."""

from typing import Final

DOMAIN: Final = "dreame_fan"

# Supported cloud model. dreame.fan.u2519 is the Dreame Bladeless Fan MF10;
# it has no published MIoT spec, so the property map below was discovered by
# scanning the Dreame Home cloud API (see tools/probe.py and docs/).
MODEL_MF10: Final = "dreame.fan.u2519"
SUPPORTED_MODELS: Final = (MODEL_MF10,)

CONF_COUNTRY: Final = "country"
CONF_DID: Final = "did"
CONF_AUTH_KEY: Final = "auth_key"

DEFAULT_COUNTRY: Final = "eu"

# Property keys are "<siid>.<piid>" strings, the format the cloud API expects.
# Only the ones whose meaning has been confirmed by observation are named here.
# The full scan, including the still-unidentified keys, lives in
# docs/miot-properties.md - move a key here once its semantics are verified.
PROP_UNKNOWN_TEMPERATURE_A: Final = "3.2"
PROP_UNKNOWN_TEMPERATURE_B: Final = "3.3"
