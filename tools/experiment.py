#!/usr/bin/env python3
"""Identify what a Dreame fan property means, by changing it and diffing.

Snapshots every known property, writes one value, snapshots again, restores the
original, and verifies the restore. Prints the diff, which is the evidence for
what the property actually controls.

    export DREAME_USER=... DREAME_PASS=...
    ./experiment.py <did> <siid.piid> <new-value>
"""

import os
import sys
import time

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "custom_components", "dreame_fan")
)
from cloud import DreameHomeCloud, DreameCloudError  # noqa: E402

KEYS = (
    "1.8 2.1 2.2 2.3 2.4 2.5 2.6 2.7 2.8 2.9 2.10 2.11 2.12 2.15 "
    "3.2 3.3 4.1 4.2 4.7 4.8 6.4 6.7 6.8 6.10 6.11 6.12 6.17 6.30"
).split()

SETTLE = 4.0


def diff(before, after, label):
    changed = {k: (before.get(k), after.get(k)) for k in KEYS if before.get(k) != after.get(k)}
    if not changed:
        print(f"  {label}: no property changed")
    for key, (old, new) in changed.items():
        print(f"  {label}: {key}  {old} -> {new}")
    return changed


def main():
    did, key, new_value = sys.argv[1], sys.argv[2], sys.argv[3]
    siid, piid = (int(part) for part in key.split("."))

    cloud = DreameHomeCloud(os.environ["DREAME_USER"], os.environ["DREAME_PASS"],
                            os.environ.get("DREAME_COUNTRY", "eu"))
    cloud.login()
    host = cloud.get_device_info(did)["bindDomain"]

    before = cloud.get_properties(did, KEYS)
    original = before.get(key)
    print(f"{key} currently {original!r}; writing {new_value!r}")

    if not cloud.set_property(did, host, siid, piid, int(new_value)):
        print("  write NOT acknowledged by the device")
        return
    time.sleep(SETTLE)

    after = cloud.get_properties(did, KEYS)
    diff(before, after, "after write")

    if after.get(key) == original:
        print(f"  NOTE: {key} did not change - the write was acknowledged but had no effect")

    print(f"restoring {key} to {original!r}")
    try:
        cloud.set_property(did, host, siid, piid, int(original))
    except DreameCloudError as err:
        print(f"  RESTORE FAILED: {err} - {key} is left at {after.get(key)!r}")
        return
    time.sleep(SETTLE)

    restored = cloud.get_properties(did, KEYS)
    if restored.get(key) == original:
        print(f"  restored, {key} back to {original!r}")
    else:
        print(f"  RESTORE INCOMPLETE: {key} is {restored.get(key)!r}, wanted {original!r}")
    diff(after, restored, "after restore")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main()
