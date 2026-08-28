# dreame.fan.u2519 (MF10) - property map

No public MIoT spec exists: `https://home.miot-spec.com/spec/dreame.fan.u2519`
returns 404, and the `dreame.fan.*` models listed on miot-spec are the older
p19xx/p20xx Mijia purifying fans. The map below was established on 2026-08-28 by
driving the fan from the Dreamehome app over ADB and watching which value moved,
one control at a time.

## Confirmed

Each of these was observed changing in response to exactly one control, and the
app's own display was checked against the value.

| key | meaning | values | writable |
|---|---|---|---|
| 2.1 | power / running state | 1 = running, 2 = off | **no** - see below |
| 2.3 | mode | 0 auto, 1 circulate, 2 sleep, 3 custom, 7 natural | yes |
| 2.4 | fan speed | 1-10 | yes, but ignored while the fan is off |
| 2.7 | oscillation | 0 / 1 | yes |
| 2.8 | active blades, bitmask | 1 left, 2 right, 3 both | yes |
| 3.2 | temperature | degC | not tested |
| 3.3 | temperature, same value as 3.2 | degC | not tested |
| 4.8 | pre-filter days remaining | app showed "Pozostało 30 dni" at value 30 | not tested |
| 6.8 | sleep timer | hours, 0 = off | yes |
| 6.10 | child lock | 0 / 1 | yes |

Notes on the confirmations:

* **Mode and speed are coupled.** Selecting a mode also sets the speed: sleep
  drops 2.4 to 1, natural to 2, circulate to 10, auto and custom to 5.
* **Temperature is real, not a coincidence.** 3.2 and 3.3 always carry the same
  number and always move together. Switching the fan off made both climb
  26 -> 27 -> 28; switching it back on made them fall 29 -> 28 -> 27 within
  twenty seconds. Nothing observed so far distinguishes 3.2 from 3.3.
* **Blades are a bitmask**, verified in both directions: turning the left blade
  off took 3 -> 2, back on 2 -> 3, then turning the right blade off took 3 -> 1.

## Power cannot be written, and the mechanism is not known

`2.1` reports power correctly and immediately, but every attempt to write it
failed, with the value unchanged each time:

* `value: 0` and `value: false` - cloud error 80001 (not delivered)
* `value: 2`, the value the app itself produces - acknowledged by the cloud, but
  the response carried results for piid 0 and piid 3 rather than piid 1, and
  2.1 stayed at 1
* `value: "2"` as a string, a batch alongside a known-good 2.4 write, `did` sent
  as `"2.1"`, and `did` sent as an integer - all rejected or ignored

Meanwhile 2.3, 2.4, 2.7, 2.8, 6.8 and 6.10 all accept writes and read back
correctly, so the write path itself works; 2.1 is specifically refused.

MIoT actions were probed on siid 2: `aiid` 1 and 2 exist and return code 0,
`aiid` 3-8 do not exist. Neither existing action changed any property.

Setting speed or mode while the fan is off does not wake it. Mode does apply
while off; speed does not.

**Unresolved.** A fan entity can expose everything except on/off until this is
answered. The remaining lead is to capture what the app actually sends when its
power button is pressed.

## Still unidentified

`1.8`, `2.2`, `2.5`, `2.6`, `2.9`, `2.10`, `2.11`, `2.12`, `2.15`, `4.1`, `4.2`,
`4.7`, `6.4`, `6.7`, `6.11`, `6.12`, `6.17`, `6.30`.

App areas not yet exercised, which is where these most likely live: the
"Wewnątrz / Na zewnątrz" toggle, the "Wygodnie" and "Temperatura" sub-screens,
the link and shuffle icons in the circulation card, and the three-dot settings
menu (display, sound, and similar).

`4.7` reads 99 next to `4.8`'s 30, so a filter percentage is plausible - but
that is a guess, not an observation.

## Method

Every property is exposed in Home Assistant as
`sensor.<device>_property_<siid>_<piid>`, so the quickest route is to watch the
entities while operating the fan one control at a time.

Without Home Assistant:

```bash
tools/probe.py scan -117222980 > /tmp/before.json
# change exactly one thing on the fan
tools/probe.py scan -117222980 > /tmp/after.json
diff <(jq -S . /tmp/before.json) <(jq -S . /tmp/after.json)
```

`tools/experiment.py <did> <siid.piid> <value>` drives a property instead:
snapshot, write, diff, restore, verify the restore.

## Do not fire MIoT actions blind - one wiped the fan's Wi-Fi setup

Probing actions on siid 2 knocked the fan off the network and it needed
re-provisioning to come back. The timeline, from the cloud responses and the
UDM's client table:

| time | event |
|---|---|
| 16:24:21 | last healthy full property read, everything nominal |
| ~16:27 | `action siid=2 aiid=1` -> code 0 |
| ~16:27 | `action siid=2 aiid=2` -> code 0, **the last command the device ever acknowledged** |
| immediately after | every further RPC returns 80001 |
| 16:29:57 | the device drops its Wi-Fi association |
| 16:29 - 16:56 | offline; broadcasting an open provisioning SSID |
| ~16:56 | back only after the owner ran "re-connect" in the Dreamehome app |

Neither action changed any property, so nothing was gained. `aiid` 3-8 do not
exist. The RPC channel died *before* the Wi-Fi association dropped, so a tight
loop of single-property reads run afterwards was knocking on a device that had
already gone - it was not the cause.

While disconnected the fan broadcast an open provisioning SSID,
`dreame-fan-u2519_miap3EC0`, whose suffix matches the last four hex digits of
its MAC; it stopped once the fan was back. **The network configuration was
genuinely lost**: the fan did not rejoin by itself, and only returned after the
owner re-ran the app's connect flow. Device state survived - all 28 properties
came back at their pre-failure values - so what the action cleared was the Wi-Fi
setup, not the settings.

Which of the two actions did it, and what either of them is for, is not
established. Both returned code 0 and changed nothing observable. Finding out
costs another re-provisioning, so leave them alone.

## Keep RPC traffic sparse

Reads go through the REST property store, which never caused trouble at any
rate. Reserve the RPC channel for writes, batch them, and leave seconds between
commands.
