# dreame.fan.u2519 (MF10) - property map

No public MIoT spec exists: `https://home.miot-spec.com/spec/dreame.fan.u2519`
returns 404, and the `dreame.fan.*` models listed on miot-spec are the older
p19xx/p20xx Mijia purifying fans, not this one. The map below therefore comes
from a brute-force scan of the Dreame Home cloud API.

Reproduce with:

```bash
export DREAME_USER=account@example.com DREAME_PASS=...   # Bitwarden: "Dreame account"
tools/probe.py scan -117222980
```

## Raw scan, 2026-08-28

Scan range siid 1-15, piid 1-30. 28 keys returned a non-null value; every other
key in the range returned nothing, which is the API's way of saying the property
does not exist.

| key | value | meaning |
|---|---|---|
| 1.8 | 0 | unidentified |
| 2.1 | 1 | unidentified |
| 2.2 | 0 | unidentified |
| 2.3 | 3 | unidentified |
| 2.4 | 5 | unidentified |
| 2.5 | 0 | unidentified |
| 2.6 | 3 | unidentified |
| 2.7 | 0 | unidentified |
| 2.8 | 0 | unidentified |
| 2.9 | 0 | unidentified |
| 2.10 | 1 | unidentified |
| 2.11 | 1 | unidentified |
| 2.12 | 0 | unidentified |
| 2.15 | 1 | unidentified |
| 3.2 | 26 | unidentified |
| 3.3 | 26 | unidentified |
| 4.1 | 100 | unidentified |
| 4.2 | 180 | unidentified |
| 4.7 | 99 | unidentified |
| 4.8 | 30 | unidentified |
| 6.4 | 0 | unidentified |
| 6.7 | 1 | unidentified |
| 6.8 | 0 | unidentified |
| 6.10 | 0 | unidentified |
| 6.11 | 1 | unidentified |
| 6.12 | 1 | unidentified |
| 6.17 | 1 | unidentified |
| 6.30 | 1 | unidentified |

Nothing in the table is labelled yet, because the scan alone cannot establish
meaning - a single snapshot of numbers is not evidence of what a number is.

## Open hypotheses (unverified)

These are guesses to test, not findings:

- `3.2` / `3.3` both read 26 and the fan advertises TempSync, so one of them is
  plausibly ambient temperature in degC. Two identical values may equally be a
  target/current pair or the same sensor exposed twice.
- `2.4` = 5 sits in the middle of the product's advertised 10 speed steps.
- `4.7` = 99 and `4.8` = 30 look like percentage/hours counters, which would fit
  the optional high-efficiency filter, but the fan on this account is the
  variant without a filter as far as we know.

## How to identify a key

Snapshot, change exactly one thing in the Dreamehome app, snapshot again, diff:

```bash
tools/probe.py scan -117222980 > /tmp/before.json
# toggle a single control in the app
tools/probe.py scan -117222980 > /tmp/after.json
diff <(jq -S . /tmp/before.json) <(jq -S . /tmp/after.json)
```

Work through the controls one at a time - power, each of the 10 speeds, each of
the 3 modes, oscillation angle, tilt, timer, child lock, display, sound - and
record the key, the value range and the enum mapping in the table above.
Anything driven from the app rather than guessed can be promoted to `const.py`.
