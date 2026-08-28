# Dreame Fan for Home Assistant

[![Version](https://img.shields.io/github/manifest-json/v/jrx-code/hassio-integration-dreame-fan/main?filename=custom_components%2Fdreame_fan%2Fmanifest.json&label=version&color=slateblue&style=for-the-badge)](https://github.com/jrx-code/hassio-integration-dreame-fan/releases)
[![HACS](https://img.shields.io/badge/HACS-custom-orange.svg?logo=HomeAssistantCommunityStore&logoColor=white&style=for-the-badge)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-41BDF5.svg?logo=home-assistant&logoColor=white&style=for-the-badge)](https://www.home-assistant.io)
[![License](https://img.shields.io/github/license/jrx-code/hassio-integration-dreame-fan?style=for-the-badge)](LICENSE)

Home Assistant integration for the **Dreame MF10** bladeless circulation fan
(`dreame.fan.u2519`). Nothing else supports this device: it is not a Mi Home
device, it has no published MIoT spec, and the existing Dreame integrations
cover the robot vacuums only.

<img src="https://raw.githubusercontent.com/jrx-code/hassio-integration-dreame-fan/main/docs/media/entities.png" width="100%">

## What works

| | |
|---|---|
| **Speed** | 10 steps, as a normal `fan` percentage |
| **Modes** | Auto, Night, Natural, Strong, Custom - the same five as F1-F5 on the remote |
| **Oscillation** | on / off |
| **Blades** | left and right, independently |
| **Airflow direction** | sync and alternating, as two switches |
| **Sleep timer** | in hours |
| **Child lock** | on / off |
| **Blade speed** | standard or fast, separate from the airflow speed |
| **LED display, key sound** | on / off |
| **Sensors** | temperature, pre-filter life (%) and days until cleaning |

<p>
<img src="https://raw.githubusercontent.com/jrx-code/hassio-integration-dreame-fan/main/docs/media/control.png" width="41%" align="top">
<img src="https://raw.githubusercontent.com/jrx-code/hassio-integration-dreame-fan/main/docs/media/integration.png" width="57%" align="top">
</p>

## What does not work

**Power on/off.** The fan reports its power state correctly and instantly, but
refuses every write to that property through the cloud API - including the exact
value the vendor's own app produces. Every other control accepts writes, so this
is specific to that one property. Rather than pretend, `turn_on` and
`turn_off` raise an error telling you to use the app or the fan's button.

Continuous monitoring behaves identically and is therefore a read-only binary
sensor rather than a switch.

If you know how the app drives power on this device, please open an issue.

## Installation

### HACS

1. HACS → three-dot menu → **Custom repositories**
2. Add `https://github.com/jrx-code/hassio-integration-dreame-fan`, category **Integration**
3. Install **Dreame Fan**, then restart Home Assistant

### Manual

Copy `custom_components/dreame_fan` into your `config/custom_components`
directory and restart Home Assistant.

## Configuration

**Settings → Devices & Services → Add Integration → Dreame Fan.**

You need the Dreamehome account the fan is already paired to, and the region it
is registered in (`eu`, `de`, `us` or `cn`). The integration then lists the
supported fans on that account and you pick one. There is nothing to put in
`configuration.yaml`.

Credentials are stored in the Home Assistant config entry, the same as any other
cloud integration.

## Entities

| Entity | Property | Notes |
|---|---|---|
| `fan` | 2.1, 2.3, 2.4, 2.7 | speed, preset mode, oscillation |
| `switch` left / right blade | 2.8 | one bitmask; each switch preserves the other's bit |
| `switch` airflow direction sync | 2.9 | |
| `switch` alternating airflow direction | 2.12 | |
| `switch` LED display | 6.12 | |
| `switch` key sound | 6.17 | |
| `switch` child lock | 6.10 | |
| `number` sleep timer | 6.8 | hours, 0 is off |
| `select` blade speed | 6.30 | standard or fast |
| `sensor` temperature | 3.2 | |
| `sensor` pre-filter life | 4.7 | percent |
| `sensor` pre-filter remaining | 4.8 | days until cleaning |
| `binary_sensor` continuous monitoring | 2.15 | read-only, see above |
| `sensor` property N.N | 11 others | raw, **disabled by default** |

Selecting a mode also moves the speed - night drops it to 1, natural to 2,
strong to 10, auto varies it. The entity shows the requested value for a few
seconds until the next poll reports what the device actually did.

### The raw property sensors

Eleven of the device's twenty-eight properties are still unidentified. They are
exposed raw, disabled by default, because eleven nameless numbers are clutter
until you are actually hunting one down.

<img src="https://raw.githubusercontent.com/jrx-code/hassio-integration-dreame-fan/main/docs/media/diagnostics.png" width="42%">

To identify one: enable it, change exactly one thing on the fan, and see which
number moves. `docs/miot-properties.md` has the table to fill in and a
command-line equivalent that needs no Home Assistant.

There is also a `dreame_fan.set_property` service for writing a raw property
by `siid.piid`, which is how the writable ones were confirmed.

## How the device actually behaves

Two findings shape the whole design, and both cost time to discover. They are
written up in [`docs/cloud-api.md`](docs/cloud-api.md):

- **The device RPC returns the wrong property's value while reporting success.**
  Asking for 2.10, 2.11 or 2.15 consistently answers with 2.1, `code: 0`, no
  error. State is therefore read only through the cloud's REST property store,
  which has never done this.
- **The REST store lags an accepted write by 35-50 seconds.** Reading back to
  confirm a write reports failure for writes that actually succeeded, so an
  accepted write is applied optimistically and reconciled by a later poll.

⚠️ **Do not probe MIoT actions on this device.** `action siid=2 aiid=2` wiped
its Wi-Fi configuration: twenty-five minutes offline, an open provisioning SSID,
and it only came back after re-running the app's connect flow. Neither action
that exists changes anything observable.

## Still to do

- [ ] Power on/off - needs someone to capture what the app sends
- [ ] Identify the remaining 11 properties: `1.8`, `2.2`, `2.5`, `2.6`, `2.10`, `2.11`, `4.1`, `4.2`, `6.4`, `6.7`, `6.11`
- [ ] Confirm the sleep timer's upper bound - 12 hours is a placeholder, not a measurement
- [ ] Work out whether 3.3 differs from 3.2 at all; both always carry the same number
- [ ] Local control - the device is cloud-bound with no miIO token, and its BLE path is unexplored
- [ ] Other models: only `dreame.fan.u2519` is claimed, because it is the only one that has been tested

## Contributing

Issues and pull requests welcome, particularly:

- a property identified, with what you changed and what moved
- the same work on another Dreame fan model
- anything about how power is actually set

Please say which firmware you are on. Everything here was established against
`1.8.30_1047`.

## Credits

The Dreame Home cloud protocol was worked out by
[Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum) for the
robot vacuums; this integration speaks the same API. The client here is a
standalone reimplementation of the handful of endpoints a fan needs, so the two
integrations do not depend on each other. The brand icon is the Dreame one from
[home-assistant/brands](https://github.com/home-assistant/brands).

## Disclaimer

Not affiliated with, endorsed by, or supported by Dreame. The API it uses is
undocumented and can change without notice.

## License

[MIT](LICENSE)
