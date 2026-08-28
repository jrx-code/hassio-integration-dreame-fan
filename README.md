# Dreame Fan for Home Assistant

Home Assistant integration for the **Dreame MF10** bladeless circulation fan
(`dreame.fan.u2519`), which no existing integration supports.

## Status

Early - recon done, no working integration yet.

- [x] Identify the device and how it is reachable (`docs/recon-2026-08-28.md`)
- [x] Standalone cloud prober that logs in and reads live properties (`tools/probe.py`)
- [x] First property scan: 28 live keys (`docs/miot-properties.md`)
- [ ] Identify what each property means, by diffing scans against app actions
- [ ] Verify writes (`set_batch_device_datas`) actually drive the fan
- [ ] Cloud client + coordinator inside `custom_components/dreame_fan`
- [ ] Config flow (account, region, device pick)
- [ ] `fan` entity: power, 10 speed steps, 3 modes, oscillation
- [ ] Sensors: temperature, wifi, whatever the scan turns out to expose
- [ ] Install on HA and add to the room dashboard

## Approach

The MF10 is not a Mi Home device and has no MIoT spec. It lives on the Dreame
Home cloud (`*.mt.eu.iot.dreame.tech`), the same API the Dreame robot vacuums
use, so the protocol work in
[Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum) applies
directly - a local checkout sits at `~/CodeHub/hassio/dreame-vacuum`.

Local control was not pursued: the device is cloud-bound with no miIO token, and
`scType` is `WIFI_BLE`. A local BLE path is unexplored.

## Probing

```bash
export BW_SESSION=$(bw unlock --raw)
export DREAME_USER=account@example.com
export DREAME_PASS=$(bw get password "Dreame account")

tools/probe.py list                # devices on the account
tools/probe.py scan -117222980     # full property scan of the MF10
tools/probe.py get -117222980 3.2,3.3
```

The prober imports the protocol from `~/CodeHub/hassio/dreame-vacuum`; point
`DREAME_VACUUM_LIB` elsewhere if that checkout moves.

## Credentials

Never in this repo. Bitwarden item **Dreame account**, account
`account@example.com`, region `eu`.
