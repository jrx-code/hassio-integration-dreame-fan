# dreame.fan.u2519 (MF10) - property map

No public MIoT spec exists: `https://home.miot-spec.com/spec/dreame.fan.u2519`
returns 404, and the `dreame.fan.*` models listed on miot-spec are the older
p19xx/p20xx Mijia purifying fans, not this one. The map below therefore comes
from probing the Dreame Home cloud API.

Reproduce with:

```bash
export DREAME_USER=account@example.com DREAME_PASS=...   # Bitwarden: "Dreame account"
tools/probe.py scan -117222980
```

## Raw scan, 2026-08-28

Scan range siid 1-15, piid 1-30. 28 keys returned a non-null value; every other
key in the range returned nothing, which is the API's way of saying the property
does not exist.

| key | value | writable | meaning |
|---|---|---|---|
| 1.8 | 0 | ? | unidentified |
| 2.1 | 1 | no (write times out) | unidentified |
| 2.2 | 0 | ? | unidentified |
| 2.3 | 3 | ? | unidentified |
| 2.4 | 5 | **yes, verified** | unidentified |
| 2.5 | 0 | ? | unidentified |
| 2.6 | 3 | ? | unidentified |
| 2.7 | 0 | ? | unidentified |
| 2.8 | 0 | ? | unidentified |
| 2.9 | 0 | ? | unidentified |
| 2.10 | 1 | ? | unidentified |
| 2.11 | 1 | ? | unidentified |
| 2.12 | 0 | ? | unidentified |
| 2.15 | 1 | ? | unidentified |
| 3.2 | 26-27 | ? | unidentified, drifts |
| 3.3 | 26-27 | ? | unidentified, drifts |
| 4.1 | 100 | ? | unidentified |
| 4.2 | 180 | ? | unidentified |
| 4.7 | 99 | ? | unidentified |
| 4.8 | 30 | ? | unidentified |
| 6.4 | 0 | ? | unidentified |
| 6.7 | 1 | ? | unidentified |
| 6.8 | 0 | ? | unidentified |
| 6.10 | 0 | ? | unidentified |
| 6.11 | 1 | ? | unidentified |
| 6.12 | 0-1 | ? | unidentified, has changed |
| 6.17 | 1 | ? | unidentified |
| 6.30 | 1 | ? | unidentified |

Nothing is labelled with a meaning yet, because nothing has been observed at
the device. Reading numbers establishes that a property exists and how it
behaves; it does not establish what it controls.

### What writing established

* **2.4 is writable.** Values 7, 8 and 9 were each accepted and read back, then
  restored to the original 5. Whether it is the speed step is still a guess.
* **2.1 is not writable through this path.** Writes of both `0` (int) and
  `false` (bool) come back as cloud error 80001, "device may be offline,
  command timed out". The value stayed at 1 throughout, so nothing was left in
  a changed state. 80001 means "not delivered", not "rejected", so this is not
  proof that the property is read-only.

### Open hypotheses (unverified)

Guesses to test, not findings:

- `3.2` / `3.3` read the same value and both moved 26 -> 27 during the session.
  Something they track drifts. The fan advertises TempSync, so ambient
  temperature in degC would fit, but two equal values could equally be a
  current/target pair or one sensor exposed twice.
- `2.4` sat at 5, in the middle of the product's advertised 10 speed steps, and
  accepts 7-9.
- `4.7` = 99 and `4.8` = 30 look like a percentage and an hours counter.

## Identifying the rest

Every property is exposed in Home Assistant as
`sensor.<device>_property_<siid>_<piid>`, so the fastest route is to watch the
entities while operating the fan by hand or from the Dreamehome app, one
control at a time: power, each speed, each of the 3 modes, oscillation, tilt,
timer, child lock, display, sound.

The same diff can be done without Home Assistant:

```bash
tools/probe.py scan -117222980 > /tmp/before.json
# change exactly one thing on the fan
tools/probe.py scan -117222980 > /tmp/after.json
diff <(jq -S . /tmp/before.json) <(jq -S . /tmp/after.json)
```

To drive a property instead, `tools/experiment.py <did> <siid.piid> <value>`
snapshots, writes, diffs, restores and verifies the restore.

Record the key, its range and its enum mapping here, then promote it to
`CONFIRMED_PROPERTIES` in `const.py` so it gets a real entity.
