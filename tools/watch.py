#!/usr/bin/env python3
"""Watch every property of a Dreame fan and print what changes, with timestamps.

`probe.py` reads once and `experiment.py` writes then diffs. This one only
watches, which is what you need when the *app* is the thing making the change:
start it, press one button in the app, and read off which properties moved and
in what order. Nothing is written and no actions are called - probing MIoT
actions on this device has knocked it off the network for 25 minutes.

The cloud's cached view lags: changes made in the app show up within about five
seconds, so a two-second poll is enough to order them, and the sequence matters
more than the absolute time.

    export DREAME_USER=... DREAME_PASS=...
    ./watch.py <did>                 # poll every 2 s until Ctrl-C
    ./watch.py <did> --interval 5
    ./watch.py <did> --keys 2.1,2.15 # only these
    ./watch.py <did> --log run.jsonl # append every snapshot for later analysis
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

from _integration import load

cloud_module = load("cloud")
const = load("const")
DreameCloudError = cloud_module.DreameCloudError
DreameHomeCloud = cloud_module.DreameHomeCloud
CONFIRMED_PROPERTIES = const.CONFIRMED_PROPERTIES
PROPERTY_KEYS = const.PROPERTY_KEYS


def label(key: str) -> str:
    """`2.1 power` for a property we have identified, plain `2.2` for the rest."""
    name = CONFIRMED_PROPERTIES.get(key)
    return f"{key} {name}" if name else key


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("did")
    parser.add_argument(
        "--interval", type=float, default=2.0, help="seconds between polls"
    )
    parser.add_argument(
        "--keys", help="comma-separated subset, default: every known property"
    )
    parser.add_argument("--log", help="append each snapshot as one JSON line")
    parser.add_argument("--country", default=os.environ.get("DREAME_COUNTRY", "eu"))
    args = parser.parse_args()

    keys = args.keys.split(",") if args.keys else list(PROPERTY_KEYS)
    cloud = DreameHomeCloud(
        os.environ["DREAME_USER"], os.environ["DREAME_PASS"], args.country
    )
    cloud.login()

    print(
        f"watching {len(keys)} properties on {args.did}, every {args.interval:g}s — Ctrl-C to stop"
    )
    previous: dict[str, str] = {}
    started = time.monotonic()
    logfile = open(args.log, "a", encoding="utf-8") if args.log else None
    try:
        while True:
            try:
                current = cloud.get_properties(args.did, keys)
            except DreameCloudError as err:
                # A transient cloud hiccup must not end a capture the user is
                # standing at the fan for.
                print(f"{datetime.now():%H:%M:%S}  ! {err}")
                time.sleep(args.interval)
                continue

            now = datetime.now()
            elapsed = time.monotonic() - started
            if logfile:
                logfile.write(
                    json.dumps(
                        {"t": now.isoformat(timespec="seconds"), "props": current}
                    )
                    + "\n"
                )
                logfile.flush()

            if not previous:
                print(f"{now:%H:%M:%S}  baseline:")
                for key in keys:
                    print(f"    {label(key):>26} = {current.get(key)}")
            else:
                changed = [k for k in keys if current.get(k) != previous.get(k)]
                for key in changed:
                    print(
                        f"{now:%H:%M:%S}  +{elapsed:6.1f}s  {label(key):>26}"
                        f"  {previous.get(key)} -> {current.get(key)}"
                    )
            previous = current
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")
        return 0
    finally:
        if logfile:
            logfile.close()


if __name__ == "__main__":
    sys.exit(main())
