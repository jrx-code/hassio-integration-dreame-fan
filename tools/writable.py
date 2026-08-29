#!/usr/bin/env python3
"""Find out which properties the device will accept a write to.

Each property is written **its own current value**, so the device is unchanged
whatever the answer, and the raw per-property reply is reported. A write to a
property known to be writable is sent immediately before every probe: when the
control succeeds and the probe fails in the same pair, the refusal belongs to
that property rather than to a busy channel.

Read the siid/piid in the reply, not just the code. This device answers ``code
0`` to some writes while naming a property nobody asked about - 6.11 comes back
as piid 1, 2.10 as two entries for other properties - and the value does not
move. Only a reply echoing the same siid/piid is an acknowledgement.

    export DREAME_USER=... DREAME_PASS=...
    ./writable.py <did> [siid.piid ...]
"""

import json
import os
import sys
import time

from _integration import load

_cloud = load("cloud")
DreameHomeCloud, DreameCloudError = _cloud.DreameHomeCloud, _cloud.DreameCloudError

DEFAULT_KEYS = ["1.8", "2.2", "2.5", "2.6", "2.10", "2.11", "6.4", "6.7", "6.11"]
CONTROL_KEY = "6.12"  # LED display, accepts writes and echoes its own address
GAP = 6.0


def raw_set(cloud, did, host, siid, piid, value):
    """set_properties, returning the whole envelope rather than a verdict."""
    gateway = f"-{host.split('.')[0]}" if host else ""
    cloud._request_id += 1
    payload = {
        "did": str(did),
        "id": cloud._request_id,
        "data": {
            "did": str(did),
            "id": cloud._request_id,
            "method": "set_properties",
            "params": [{"did": str(did), "siid": siid, "piid": piid, "value": value}],
        },
    }
    try:
        return cloud._call(f"dreame-iot-com{gateway}/device/sendCommand", payload, timeout=30)
    except DreameCloudError as err:
        return {"code": None, "_error": str(err)}


def echoed(result, siid, piid):
    """True when the device answered about the property we actually wrote."""
    entries = ((result or {}).get("data") or {}).get("result") or []
    return any(e.get("siid") == siid and e.get("piid") == piid and e.get("code") == 0
               for e in entries)


def main():
    did = sys.argv[1]
    keys = sys.argv[2:] or DEFAULT_KEYS

    cloud = DreameHomeCloud(os.environ["DREAME_USER"], os.environ["DREAME_PASS"],
                            os.environ.get("DREAME_COUNTRY", "eu"))
    cloud.login()
    host = cloud.get_device_info(did)["bindDomain"]

    before = cloud.get_properties(did, keys + [CONTROL_KEY])
    control_siid, control_piid = (int(p) for p in CONTROL_KEY.split("."))

    for key in keys:
        current = before.get(key)
        if current is None:
            print(f"{key:>5}  the store has no value, skipped")
            continue
        siid, piid = (int(p) for p in key.split("."))

        control = raw_set(cloud, did, host, control_siid, control_piid,
                          int(before[CONTROL_KEY]))
        control_ok = echoed(control, control_siid, control_piid)
        time.sleep(GAP)

        result = raw_set(cloud, did, host, siid, piid, int(current))
        verdict = "writable" if echoed(result, siid, piid) else "refused"
        if not control_ok:
            verdict += " (CONTROL ALSO FAILED - inconclusive)"

        print(f"{key:>5}  value={current!r:>5}  {verdict}")
        print(f"       {json.dumps(result)[:200]}")
        time.sleep(GAP)

    after = cloud.get_properties(did, keys + [CONTROL_KEY])
    moved = {k: (before.get(k), after.get(k)) for k in keys if before.get(k) != after.get(k)}
    print("\nvalues moved during the probe:", moved or "none")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main()
