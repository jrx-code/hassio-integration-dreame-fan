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
| 2.15 | "Ciągłe monitorowanie" | 0 / 1 | **no** - 80001, same as 2.1 |
| 2.3 | mode | see the mode table below | yes |
| 2.4 | fan speed | 1-10 | yes, but ignored while the fan is off |
| 2.7 | oscillation | 0 / 1 | yes |
| 2.8 | active blades, bitmask | 1 left, 2 right, 3 both | yes |
| 2.9 | airflow direction sync, "Synchronizacja kierunku nawiewu" | 0 / 1 | yes |
| 2.12 | alternating airflow direction, "Naprzemienny kierunek nawiewu" | 0 / 1 | yes |
| 3.2 | temperature | degC | not tested |
| 3.3 | temperature, same value as 3.2 | degC | not tested |
| 4.7 | pre-filter life, percent | app: "Żywotność filtra w 99%" at value 99 | not tested |
| 4.8 | days until pre-filter cleaning | app: "Szac. pozostało 30 dni do czyszczenia" | not tested |
| 6.12 | "Wyświetlacz LED" | 0 / 1 | yes |
| 6.17 | "Dźwięk klawisza" | 0 / 1 | yes |
| 6.30 | "Prędkość łopatek" | 1 standard, 2 fast | yes |
| 6.8 | sleep timer | hours, 0 = off | yes |
| 6.10 | child lock | 0 / 1 | yes |

Notes on the confirmations:

* **Mode and speed are coupled.** Selecting a mode also sets the speed: night
  drops 2.4 to 1, natural to 2, strong to 10. Auto varies it - observed at both
  3 and 5, which is what an automatic mode would be expected to do.

### Modes

Values confirmed by tapping each one in the app and reading both the label it
displays and 2.3. The order matches F1-F5 on the physical remote.

| remote | app label (pl) | 2.3 | speed it sets |
|---|---|---|---|
| F1 | Auto | 0 | varies |
| F2 | Tryb nocny | 2 | 1 |
| F3 | Tryb naturalny | 7 | 2 |
| F4 | Tryb Mocny | 1 | 10 |
| F5 | Tryb niestandardowy | 3 | left as-is |

Note the values are not in picker order: strong is 1 and natural is 7.
* **Temperature is real, not a coincidence.** 3.2 and 3.3 always carry the same
  number and always move together. Switching the fan off made both climb
  26 -> 27 -> 28; switching it back on made them fall 29 -> 28 -> 27 within
  twenty seconds. Nothing observed so far distinguishes 3.2 from 3.3.
* **The two direction flags live in the circulation card.** Both were named by
  tapping the small icons between the blades and reading the label the app then
  shows: the chain icon is 2.9, the shuffle icon is 2.12. The app offers them as
  alternatives - turning one on replaces the two-blade view with a single merged
  control - but the device accepts both set at once, and the app then renders a
  mixed state (2.9's label with 2.12's icon) that it cannot produce itself. They
  are independent flags on the wire.
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

`1.8`, `2.2`, `2.5`, `2.6`, `2.10`, `2.11`, `6.4`, `6.7`, `6.11`. `4.1` and `4.2`
were the composite filter and left this list in v0.5.0.

App areas not yet exercised, which is where these most likely live: the
"Wewnątrz / Na zewnątrz" toggle, the "Wygodnie" and "Temperatura" sub-screens,
and "Inteligentne ustawienia scen" under the three-dot menu. The rest of that
settings menu is now accounted for: continuous monitoring, key sound, LED
display and blade speed.

### Which of the nine accept a write

Established on 2026-08-29 by writing each property **its own current value** -
a no-op whatever the answer - and reading the raw per-property code back. A
write to 6.12, which is known to work, was sent immediately before every probe,
so a refusal cannot be blamed on a tired channel. Every value was identical
before and after.

| key | value | answer | writable |
|---|---|---|---|
| 1.8 | 0 | `code 0`, echoed as `siid 1, piid 8` | **yes** |
| 2.2 | 0 | 80001 | no |
| 2.5 | 0 | 80001 | no |
| 2.6 | 3 | 80001 | no |
| 2.10 | 1 | `code 0`, but answered for `siid 2 piid 0` **and** `siid 0 piid 1` | no |
| 2.11 | 1 | 80001 | no |
| 6.4 | 0 | 80001 | no |
| 6.7 | 1 | 80001 | no |
| 6.11 | 1 | `code 0`, but answered for `siid 6, piid 1` | no |

The control write answered `code 0` echoed as `siid 6, piid 12` in all nine
pairs, so the channel was healthy throughout.

**Read the siid/piid back, not just the code.** 2.10 and 6.11 look like
successes until you check which property the device replied about: 6.11 comes
back as piid 1, and 2.10 as two entries for properties nobody asked about. This
is the same signature 2.1 produces, where a write "acknowledged" as piid 0 and
piid 3 left 2.1 untouched. Only 1.8 echoed its own address.

1.8 is genuinely writable, not merely tolerant of a no-op: `experiment.py
<did> 1.8 1` moved it 0 -> 1, read it back, and restored it to 0, with the
device online and every other property untouched throughout. What it *does* is
still open - no other property responded in the four seconds the flag was held,
so whatever it affects is not visible in the property store.

It is also the only populated property in the whole of `siid 1`: piid 1-30 were
read and only piid 8 came back with a value. That is where the MIoT convention
would put Device Information, but the string fields a device-information service
would carry are absent - which may only mean the REST store does not cache them,
so it is not evidence either way.

### Two properties refuse writes, not one

2.1 and 2.15 both answer 80001 to every write through the cloud property API,
and both are freely toggleable in the app - so this is the API's limit rather
than the device's. Everything else that was tried accepts writes. 2.15 is
therefore exposed as a binary sensor, not a switch.

### 2.1 and 2.3 flip together, on their own

Watched on 2026-08-29 with nobody in the room and nothing writing to the fan.
Two windows, sampled from the cloud property store: 44 reads four seconds apart,
and 58 reads ten seconds apart over the following twelve minutes. Power and mode
change **atomically and only with each other**, under a single `updateDate`.

| 2.1 | 2.3 | 4 s window | 10 s window |
|---|---|---|---|
| 1 (on) | 3 (custom) | 36 | 44 |
| 2 (off) | 0 (auto) | 8 | 14 |

There is not one sample in either window where one moved without the other.
2.4 and 2.15 never moved at all, and neither did any of the nine unidentified
properties. Home Assistant polls every 30 seconds, so it lands on whichever
bundle is current and the fan entity looks like it is switching itself on and
off every minute or two - visible in the recorder from 08:46 onwards.

3.2/3.3 are *not* part of the bundle. In a third window - all 28 properties,
every three seconds for eleven minutes, no read errors - power and mode changed
18 times each and always on the same sample, while the two temperatures changed
20 times. Twice the temperature moved a sample before the pair and twice a
sample after it. The temperature also bounces on its own: 25 -> 24 -> 25 inside
three seconds at 11:54:44.

Nothing else moved at all in those eleven minutes. All 24 remaining properties,
the nine unidentified ones included, held their value for the whole window.

### It is not a proximity sensor

The same eleven-minute window covers a person leaving the room, staying out, and
walking back in at a known time. Flips per minute ran 3, 5, 2, 0, 2, 2, 0, 4:
the busiest minute happened with the room empty and two minutes were completely
still, also with the room empty. The rate does not track presence, and no
property responds to a person being there. If this fan senses people, it does
not report it through any of its 28 properties.

### The flip was a smart scene running on the fan itself

The cause is a rule stored on the device under "Inteligentne ustawienia scen",
reached from the three-dot menu in the app. The owner's rule was named *FanON*,
and the app's notification list was full of "task FanON completed" entries with
timestamps, which is the rule firing over and over.

Deleting it stopped the flip dead. Same 28 properties, same three-second
sampling, same fan:

| | before | after the rule was deleted |
|---|---|---|
| window | 11 min | 6 min |
| 2.1 / 2.3 changes | 18 each, always paired | **0** |
| 3.2 / 3.3 | 20 changes, bouncing 25-24-25 within 3 s | one step, 25 -> 26 |
| the other 24 properties | no change | no change |

The temperature is the tell. While the rule ran it jittered between 24 and 25;
with the rule gone it climbed 25 -> 26 and stayed there, which is what the doc
above describes for a fan that is genuinely off and no longer stirring the air.

Two things made this hard to find. These rules live **on the device** and do not
appear in the scene API: `getSceneByHomeV2` lists only the cloud scenes, and the
account's two automatic ones were both `enabled: 0`, which looked like proof
that no automation existed. And the flip is invisible from the property store
alone - nothing records that a rule fired, only the state it leaves behind.

**So before blaming the cloud for a device that changes state on its own, open
the app's smart scene list and its notification log.** The evidence is there and
nowhere in the API.

### Identity fields

The app's device-info screen lists model, MAC, S/N, DID, UID, firmware and a
plugin version. All but two come straight out of `device/info`. **The serial
only appears in `listV2`** - `device/info` returns `sn: null` - so the
integration falls back to the device list for it. The plugin version (137) is
not in the API at all; `extensionId` is 2416, a different number.

`4.7` reads 99 next to `4.8`'s 30, so a filter percentage is plausible - but
that is a guess, not an observation.

## Method

Every property is exposed in Home Assistant as
`sensor.<device>_property_<siid>_<piid>`, so the quickest route is to watch the
entities while operating the fan one control at a time.

Without Home Assistant:

```bash
tools/probe.py scan <did> > /tmp/before.json
# change exactly one thing on the fan
tools/probe.py scan <did> > /tmp/after.json
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
`dreame-fan-u2519_miapXXXX`, whose suffix matches the last four hex digits of
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
