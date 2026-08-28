# Dreame Fan for Home Assistant

Home Assistant integration for the **Dreame MF10** bladeless circulation fan
(`dreame.fan.u2519`), which no existing integration supports.

## Status

Working. Everything the device exposes is controllable except power.

- [x] Identify the device and how it is reachable (`docs/recon-2026-08-28.md`)
- [x] Standalone cloud client, no dependency on other integrations (`cloud.py`)
- [x] Config flow: account, region, pick the fan
- [x] 17 of 28 properties identified (`docs/miot-properties.md`)
- [x] `fan` entity: speed 1-10, five modes, oscillation
- [x] Switches: child lock, the two blades, direction sync, alternating direction, LED display, key sound
- [x] Number: sleep timer
- [x] Sensors: temperature, pre-filter days, plus the 11 unidentified properties raw (disabled by default)
- [x] `dreame_fan.set_property` service for writing a raw property
- [x] Brand icon, taken from the Dreame Vacuum brand
- [x] Verified end to end against a real MF10 on HA 2026.7.4
- [ ] Power on/off - the device rejects every write to 2.1
- [ ] Identify the remaining 11 properties

## Entities

| entity | property | notes |
|---|---|---|
| `fan` | 2.1, 2.3, 2.4, 2.7 | speed, preset mode, oscillation. On/off raises an error - see below |
| `switch` child lock | 6.10 | |
| `switch` left / right blade | 2.8 | one bitmask, each switch preserves the other's bit |
| `switch` direction sync | 2.9 | the app's "Synchronizacja kierunku nawiewu" |
| `switch` alternating direction | 2.12 | the app's "Naprzemienny kierunek nawiewu" |
| `number` sleep timer | 6.8 | hours, 0 is off. Upper bound not verified against the device |
| `sensor` temperature | 3.2 | |
| `sensor` pre-filter remaining | 4.8 | days until cleaning |
| `sensor` pre-filter life | 4.7 | percent |
| `select` blade speed | 6.30 | standard or fast - the blades' own travel speed, not airflow |
| `switch` LED display / key sound | 6.12, 6.17 | |
| `binary_sensor` continuous monitoring | 2.15 | read-only: the API refuses writes to it |
| `sensor` property N.N | the other 11 | raw, diagnostic, **disabled by default** |

The eleven raw property sensors are off out of the box - they exist to identify
what is left, not for daily use. Enable the ones you want in the entity
registry, change one thing on the fan, and see which number moves.

## Installation

Add this repository to HACS as a custom repository of type Integration, install
it, restart Home Assistant, then add **Dreame Fan** from Settings > Devices &
Services. You will need the Dreamehome account the fan is paired to, and its
region.

The five preset modes are the app's own, and line up with F1-F5 on the remote:
auto, night, natural, strong, custom. Selecting one also moves the speed - night
drops it to 1, natural to 2, strong to 10, auto varies it - so the entity shows
the requested speed for a few seconds until the next poll reports what the
device actually did.

**Power is not wired up.** 2.1 reports the state correctly and immediately, but
the device rejects every write to it, including the value the app itself
produces. `turn_on` and `turn_off` therefore raise an error rather than pretend
to work. Continuous monitoring (2.15) behaves the same way and is a read-only
binary sensor for that reason. Everything else accepts writes.

## Approach

The MF10 is not a Mi Home device and has no MIoT spec. It lives on the Dreame
Home cloud, the same API the Dreame robot vacuums use, so the protocol work in
[Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum) applies -
though `cloud.py` reimplements the handful of endpoints a fan needs rather than
depending on that integration being installed.

Two findings shape the design, both documented in `docs/cloud-api.md`:

* The device RPC returns **wrong values for some properties while reporting
  success**, so state is read only through the cloud's REST property store.
* The REST store **lags an acknowledged write by 35-50 seconds**, so an
  accepted write is applied optimistically and reconciled by a later poll.

Local control was not pursued: the device is cloud-bound with no miIO token.
A local BLE path is unexplored.

## Identifying the properties

This is the open work, and it needs eyes on the device. Every property appears
as `sensor.<device>_property_<siid>_<piid>`. Operate the fan one control at a
time and watch which entity moves. See `docs/miot-properties.md` for the table
to fill in and for the command-line equivalent.

## Probing outside Home Assistant

```bash
export BW_SESSION=$(bw unlock --raw)
export DREAME_USER=you@example.com
export DREAME_PASS=$(bw get password "Dreame account")

tools/probe.py list                      # devices on the account
tools/probe.py scan <did>           # full property scan
tools/experiment.py <did> 2.4 8     # write, diff, restore, verify
```

`probe.py` imports the protocol from `~/CodeHub/hassio/dreame-vacuum`; point
`DREAME_VACUUM_LIB` elsewhere if that checkout moves. `experiment.py` uses this
integration's own `cloud.py` and needs nothing else.

## Credentials

Never in this repo. your password manager, account
`you@example.com`, region `eu`.
