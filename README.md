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

Continuous monitoring (2.15) refuses every write with `80001`, exactly as power
did, and is therefore a read-only binary sensor rather than a switch. Power
itself now works, through a different mechanism - see
[Power, and why it goes through a scene](#power-and-why-it-goes-through-a-scene).

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
| `fan` | 2.1, 2.3, 2.4, 2.7 | power (via scenes), speed, preset mode, oscillation |
| `switch` left / right blade | 2.8 | one bitmask; each switch preserves the other's bit |
| `switch` airflow direction sync | 2.9 | |
| `switch` alternating airflow direction | 2.12 | |
| `switch` LED display | 6.12 | |
| `switch` key sound | 6.17 | |
| `switch` child lock | 6.10 | |
| `number` sleep timer | 6.8 | hours, 0 is off |
| `select` blade speed | 6.30 | standard or fast |
| `sensor` airflow | 2.4 | live 0-10, whatever the mode is doing |
| `sensor` temperature | 3.2 | |
| `sensor` pre-filter life | 4.7 | percent |
| `sensor` composite filter life | 4.1 | percent, the optional HEPA filter |
| `sensor` composite filter remaining | 4.2 | days, 180 = the six months the app quotes |
| `sensor` pre-filter remaining | 4.8 | days until cleaning |
| `binary_sensor` continuous monitoring | 2.15 | read-only, see above |
| `sensor` property N.N | 11 others | raw, **disabled by default** |

### Speed is not a setpoint, except in custom mode

Property 2.4 reads the airflow the fan is producing **right now**. Measured by
driving the fan from the app and the remote while polling every property every
two seconds (203 samples with the fan running, `tools/watch.py`):

| Mode | Samples | 2.4 |
|---|---|---|
| natural | 121 | 0, 1, 2, 3, 4 - walks continuously, by design |
| strong | 20 | 10, fixed by the mode |
| night | 2 | 1, fixed by the mode |
| auto | 1 | 3, the device's own choice |
| custom | 60 | 7, then 2 - exactly what was set |

Selecting a mode moves 2.4 in the same poll; there is no second property holding
a per-mode speed, and custom remembers its own last value (leaving custom at 2
and returning put it straight back to 2).

The `fan` entity's percentage is a **control**, so in natural mode it holds the
last value seen in any other mode instead of following the fan's own variation -
a slider that moves by itself every poll fights the user and fills the recorder.
Everywhere else it shows the live number, which the mode holds steady anyway.
`sensor` airflow always carries the live value, natural mode included.

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

## Power, and why it goes through a scene

Property 2.1 reports power correctly and instantly, and refuses every write to
it: `80001`, *device did not acknowledge*, whether the fan is running or
stopped, in the same session and against the same gateway where a write to 6.12
is accepted and read back a second later. Value, type, batching and a second
`did` make no difference.

The vendor's app does not write that property either. It runs a **scene**. The
cloud publishes what a scene may tell a given device to do:

```
POST /dreame-user-iot/smarthome/scene/action/getDeviceCommand  {"did": ..., "model": ...}
  157  Speed   range 1-10
  159  Switch  enum -> 161 Off, 163 On
  165  Mode    enum -> 167 AI Purify, 169 Turbo, 171 Sleep, 173 Natural
```

So this integration keeps two scenes of its own, `HA <device> ON` and
`HA <device> OFF`, creates them on first use and runs them with
`smarthome/scene/startSceneAction`. The fan stops or starts about five seconds
later. They are ordinary manual scenes, they show up in the app, and deleting
them only means the integration makes them again.

Two traps on the way there, both of which answer `code: 0`:

- `saveCommandAction` looks like the endpoint that attaches a command to a
  scene. It accepts anything and stores nothing. The action has to be part of
  the `saveOrUpdate` payload for the whole scene.
- inside that payload the command's key is `id`, not `commandId`, and it needs
  `detailType`:
  `"detail": [{"id": "159", "detailType": "enum", "value": "163"}]`.

`turn_on` waits about six seconds after the scene before applying a speed or
preset that came with the call, because the fan discards those while stopped.

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

- [ ] Identify the remaining 9 properties: `1.8`, `2.2`, `2.5`, `2.6`, `2.10`, `2.11`, `6.4`, `6.7`, `6.11`. Every control the app offers has been driven while polling all 28 properties; none of them moves these, so they are internal
- [ ] Find where "the composite filter is fitted" is stored. Marking one as fitted in the app makes its card appear on the device page reading 180 days - which is 4.2 - but **no** property changed: all 28 were polled every two seconds across the click, and `iotuserdata/getDeviceData` holds only `s_pri_plugin` and `s_auth_config`. So the flag is app- or cloud-side, and 4.1/4.2 count regardless of whether a filter is actually in there
- [ ] The app's "Indoor / Outdoor" switch changes no property at all (44 polls across both positions): it selects which air data the app displays, nothing on the device
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
