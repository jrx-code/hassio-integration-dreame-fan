# Dreame Home cloud API, as it behaves for a fan

Everything here was checked against `dreame.fan.u2519` firmware `1.8.30_1047`
on 2026-08-28. The endpoint names come from the encoded string table in
`dreame-vacuum`'s `protocol.py`; `custom_components/dreame_fan/cloud.py`
implements the subset a fan needs in plain form.

## Endpoints used

| Purpose | Path |
|---|---|
| Login / refresh | `POST {api}/dreame-auth/oauth/token` (form-encoded) |
| Device list | `POST {api}/dreame-user-iot/iotuserbind/device/listV2` |
| Device info | `POST {api}/dreame-user-iot/iotuserbind/device/info` |
| Property read | `POST {api}/dreame-user-iot/iotstatus/props` |
| Device RPC | `POST {api}/dreame-iot-com-<gateway>/device/sendCommand` |

`{api}` is `https://<region>.iot.dreame.tech:13267`. `<gateway>` is the first
label of the device's `bindDomain`, so `10000.mt.eu.iot.dreame.tech:19973`
gives `dreame-iot-com-10000`.

Login sends the password as `md5(password + "RAylYC%fmSKp7%Tq")`. Subsequent
calls carry the access token in a `Dreame-Auth` header, plus the app's static
`Authorization: Basic ...` and a `Tenant-Id`.

## The RPC read path is unsafe - use REST for state

The device RPC (`sendCommand` with `get_properties`) answers some keys with
another property's value and reports success while doing it:

```
asked 6.30 -> got 6.30=1
asked 2.10 -> got 2.1=1
asked 6.17 -> got 6.17=1
asked 2.10 -> got 2.1=1
asked 2.10 -> got 2.1=1
asked 6.30 -> got 6.30=1
asked 2.11 -> got 2.1=1
asked 2.11 -> got 2.1=1
```

Every one of those came back with `code: 0` and no error. It is deterministic
and repeatable, not a stale response being mismatched to the wrong request:
interleaving a key that answers correctly with one that does not returns the
same wrong answer every time. `2.12`, `6.12`, `6.17` and `6.30` are two-digit
piids that answer correctly, so it is not simple truncation of the piid either.

The REST property store (`iotstatus/props`) returned all 28 keys with correct
labels on every attempt. **This integration reads state only through REST, and
uses the RPC only to write.**

## Other behaviour worth knowing

* **`props` does not enumerate.** Keys must be listed explicitly as
  `siid.piid`. Passing `""`, `"*"` or `"all"` returns empty or echoes the
  literal key. That is why discovery is a brute-force scan.
* **No history.** `iotstatus/history` returns `{"code": 0, "data": {"list": []}}`
  for every property over a 14-day window. The cloud keeps nothing for this
  device, so historical values cannot be used to characterise a property.
* **The named data store is not device state.** `iotuserdata/getDeviceData`
  ignores the key filter entirely and returns the same single entry,
  `prop.s_auth_config`, for `[]`, `["*"]`, `["all"]` and `["prop.*"]` alike.
* **Writes lag the cached read.** After an acknowledged write, `props` kept
  returning the old value and only caught up somewhere between 35 and 50
  seconds later. Reading back immediately to confirm a write reports failure
  for a write that actually succeeded, so the coordinator applies an
  acknowledged write optimistically and reconciles on a later poll.
* **Error 80001** (`设备可能不在线，指令发送超时`) is the cloud saying the
  device did not answer in time. It means the command was not delivered, not
  that it was refused.
* **Batch size matters.** An RPC `get_properties` for all 28 keys at once
  returned null; batches of six worked.

## Local dependencies of the prober

`tools/probe.py` imports the protocol from a `dreame-vacuum` checkout and stubs
`miio` and `paho.mqtt`, neither of which the REST path needs. The stub is
load-bearing on the XPS laptop, where the local `pyOpenSSL` raises
`module 'lib' has no attribute 'GEN_EMAIL'` and importing paho drags it in via
`dns.resolver`. The integration itself has no such dependency: `cloud.py` is
standalone and needs only `requests`.
