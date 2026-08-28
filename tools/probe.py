#!/usr/bin/env python3
"""Standalone prober for Dreame Home cloud devices.

Reuses the cloud protocol implementation shipped with Tasshack/dreame-vacuum
(the MF10 speaks the same Dreame Home API as the vacuums), without pulling in
Home Assistant. Used to discover the MIoT property map of dreame.fan.u2519,
for which no public spec exists on home.miot-spec.com.

Usage:
    export DREAME_USER=... DREAME_PASS=...
    ./probe.py list                 # enumerate devices on the account
    ./probe.py scan <did>           # brute-force siid 1..15 / piid 1..30
    ./probe.py get <did> 2.1,2.4    # read specific properties
"""

import importlib.util
import json
import logging
import os
import sys
import types

DREAME_VACUUM_LIB = os.environ.get(
    "DREAME_VACUUM_LIB",
    os.path.expanduser(
        "~/CodeHub/hassio/dreame-vacuum/custom_components/dreame_vacuum/dreame"
    ),
)
COUNTRY = os.environ.get("DREAME_COUNTRY", "eu")


def load_protocol():
    """Import dreame/protocol.py standalone, stubbing deps it only needs locally."""
    # python-miio backs the local miIO transport; cloud-only use never touches it.
    miio = types.ModuleType("miio")
    miioprotocol = types.ModuleType("miio.miioprotocol")

    class MiIOProtocol:  # noqa: D401 - stub
        pass

    miioprotocol.MiIOProtocol = MiIOProtocol
    miio.miioprotocol = miioprotocol
    sys.modules.setdefault("miio", miio)
    sys.modules.setdefault("miio.miioprotocol", miioprotocol)

    # paho is imported at module level but only used for the live MQTT stream.
    # Stub it so a broken local paho/pyOpenSSL cannot block plain REST calls.
    try:
        from paho.mqtt.client import Client  # noqa: F401
    except Exception:
        paho = types.ModuleType("paho")
        mqtt = types.ModuleType("paho.mqtt")
        client = types.ModuleType("paho.mqtt.client")

        class Client:  # noqa: D401 - stub
            def __init__(self, *args, **kwargs):
                pass

        client.Client = Client
        mqtt.client = client
        paho.mqtt = mqtt
        sys.modules["paho"] = paho
        sys.modules["paho.mqtt"] = mqtt
        sys.modules["paho.mqtt.client"] = client

    pkg = types.ModuleType("dreamelib")
    pkg.__path__ = [DREAME_VACUUM_LIB]
    pkg.VERSION = "probe"
    sys.modules["dreamelib"] = pkg

    exceptions = types.ModuleType("dreamelib.exceptions")

    class DeviceException(Exception):
        pass

    exceptions.DeviceException = DeviceException
    sys.modules["dreamelib.exceptions"] = exceptions

    spec = importlib.util.spec_from_file_location(
        "dreamelib.protocol", os.path.join(DREAME_VACUUM_LIB, "protocol.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["dreamelib.protocol"] = module
    spec.loader.exec_module(module)
    return module


def connect(did=None, model=None):
    user = os.environ.get("DREAME_USER")
    password = os.environ.get("DREAME_PASS")
    if not user or not password:
        sys.exit("Set DREAME_USER and DREAME_PASS (see your password manager).")

    protocol = load_protocol()
    cloud = protocol.DreameVacuumDreameHomeCloudProtocol(
        user, password, "dreame", COUNTRY, did=did
    )
    if not cloud.login():
        sys.exit(f"Login failed (country={COUNTRY}, auth_failed={cloud.auth_failed}).")
    if did:
        cloud._model = model or "dreame.fan.u2519"
        cloud.get_device_info()
    return cloud


def cmd_list():
    data = connect().get_devices()
    for record in data["page"]["records"]:
        info = record.get("deviceInfo") or {}
        print(
            f"{record['model']:<24} did={record['did']:<14} "
            f"online={record['online']!s:<5} "
            f"name={record['customName'] or info.get('displayName', '')}"
        )


def cmd_scan(did):
    cloud = connect(did)
    found = {}
    for siid in range(1, 16):
        keys = ",".join(f"{siid}.{piid}" for piid in range(1, 31))
        for item in cloud.get_properties(keys) or []:
            if isinstance(item, dict) and item.get("value") is not None:
                found[item["key"]] = item["value"]
    print(json.dumps(found, indent=2))


def cmd_get(did, keys):
    print(json.dumps(connect(did).get_properties(keys), indent=2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    argv = sys.argv[1:]
    if not argv:
        sys.exit(__doc__)
    if argv[0] == "list":
        cmd_list()
    elif argv[0] == "scan":
        cmd_scan(argv[1])
    elif argv[0] == "get":
        cmd_get(argv[1], argv[2])
    else:
        sys.exit(__doc__)
