"""Minimal client for the Dreame Home cloud API.

Deliberately standalone: the protocol is the same one Tasshack/dreame-vacuum
speaks, but this integration must not depend on that integration being
installed, so the handful of endpoints a fan needs are implemented here in
plain form.

Two transports, and the difference matters:

* REST property store (``iotstatus/props``) - the cloud's cached view of the
  device. Reliable, correctly labelled, and what this integration reads.
* Device RPC (``device/sendCommand``) - forwarded to the device itself. This is
  the only way to *write*, but it is not trustworthy for reads: on
  dreame.fan.u2519 firmware 1.8.30_1047, reading 2.10/2.11/2.15 returns the
  value of 2.1 with ``code: 0`` and no error of any kind. Never read state
  through the RPC path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

import requests

_LOGGER = logging.getLogger(__name__)

API_PORT = "13267"
API_HOST_SUFFIX = ".iot.dreame.tech"
PASSWORD_SALT = "RAylYC%fmSKp7%Tq"
USER_AGENT = "Dreame_Smarthome/2.1.9 (iPhone; iOS 18.4.1; Scale/3.00)"
BASIC_AUTH = "Basic ZHJlYW1lX2FwcHYxOkFQXmR2QHpAU1FZVnhOODg="
DEFAULT_TENANT = "000000"

TOKEN_PATH = "/dreame-auth/oauth/token"
DEVICE_LIST_PATH = "dreame-user-iot/iotuserbind/device/listV2"
DEVICE_INFO_PATH = "dreame-user-iot/iotuserbind/device/info"
PROPS_PATH = "dreame-user-iot/iotstatus/props"

REQUEST_TIMEOUT = 15


class DreameCloudError(Exception):
    """Raised when the cloud API cannot be used."""


class DreameAuthError(DreameCloudError):
    """Raised when credentials are rejected."""


class DreameHomeCloud:
    """Synchronous Dreame Home cloud client. Call from an executor."""

    def __init__(self, username: str, password: str, country: str = "eu") -> None:
        self._username = username
        self._password = password
        self._country = country
        self._session = requests.Session()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0
        self._tenant_id: str = DEFAULT_TENANT
        self._uid: str | None = None
        self._request_id = 1

    @property
    def api_url(self) -> str:
        return f"https://{self._country}{API_HOST_SUFFIX}:{API_PORT}"

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Language": "en-US;q=0.8",
            "User-Agent": USER_AGENT,
            "Authorization": BASIC_AUTH,
            "Tenant-Id": self._tenant_id,
        }

    def login(self) -> None:
        """Obtain an access token. Uses the refresh token when one is held."""
        if self._refresh_token:
            body = f"platform=IOS&scope=all&grant_type=refresh_token&refresh_token={self._refresh_token}"
        else:
            digest = hashlib.md5((self._password + PASSWORD_SALT).encode()).hexdigest()
            body = (
                "platform=IOS&scope=all&grant_type=password"
                f"&username={self._username}&password={digest}&type=account"
            )

        headers = self._auth_headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        try:
            response = self._session.post(
                self.api_url + TOKEN_PATH,
                headers=headers,
                data=body,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as err:
            raise DreameCloudError(f"Cannot reach the Dreame cloud: {err}") from err

        if response.status_code != 200:
            # An expired refresh token is recoverable: fall back to the password.
            if self._refresh_token:
                self._refresh_token = None
                self.login()
                return
            raise DreameAuthError(f"Login rejected ({response.status_code})")

        data = response.json()
        if "access_token" not in data:
            raise DreameAuthError("Login response carried no access token")

        self._access_token = data["access_token"]
        self._refresh_token = data.get("refresh_token")
        self._expires_at = time.time() + data.get("expires_in", 3600) - 120
        self._tenant_id = data.get("tenant_id", self._tenant_id)
        self._uid = data.get("uid")

    def _call(self, path: str, payload: dict | None = None, timeout: int = REQUEST_TIMEOUT) -> Any:
        if not self._access_token or time.time() > self._expires_at:
            self.login()

        headers = self._auth_headers()
        headers["Content-Type"] = "application/json"
        headers["Dreame-Auth"] = self._access_token

        try:
            response = self._session.post(
                f"{self.api_url}/{path}",
                headers=headers,
                data=json.dumps(payload, separators=(",", ":")) if payload is not None else None,
                timeout=timeout,
            )
        except requests.RequestException as err:
            raise DreameCloudError(f"Request to {path} failed: {err}") from err

        if response.status_code == 401:
            self._access_token = None
            self.login()
            return self._call(path, payload, timeout)
        if response.status_code != 200:
            raise DreameCloudError(f"{path} returned HTTP {response.status_code}")

        return response.json()

    def get_devices(self) -> list[dict]:
        """Every device bound to the account."""
        result = self._call(DEVICE_LIST_PATH)
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Device list failed: {result}")
        return result["data"]["page"]["records"]

    def get_device_info(self, did: str) -> dict:
        result = self._call(DEVICE_INFO_PATH, {"did": str(did)})
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Device info failed: {result}")
        return result["data"]

    def get_properties(self, did: str, keys: list[str]) -> dict[str, str]:
        """Read properties from the cloud's cached store.

        ``keys`` are ``"<siid>.<piid>"`` strings and must be listed explicitly:
        the endpoint does not enumerate, and "", "*" and "all" all come back
        empty rather than returning everything.
        """
        result = self._call(PROPS_PATH, {"did": str(did), "keys": ",".join(keys)})
        if not result or "data" not in result:
            raise DreameCloudError(f"Property read failed: {result}")
        return {
            item["key"]: item["value"]
            for item in result["data"]
            if isinstance(item, dict) and item.get("value") is not None
        }

    def set_property(self, did: str, host: str, siid: int, piid: int, value: Any) -> bool:
        """Write one property through the device RPC.

        ``host`` is the device's ``bindDomain``; its leading label selects the
        command gateway. Returns True when the device acknowledged with code 0.
        """
        gateway = f"-{host.split('.')[0]}" if host else ""
        self._request_id += 1
        payload = {
            "did": str(did),
            "id": self._request_id,
            "data": {
                "did": str(did),
                "id": self._request_id,
                "method": "set_properties",
                "params": [{"did": str(did), "siid": siid, "piid": piid, "value": value}],
            },
        }
        result = self._call(f"dreame-iot-com{gateway}/device/sendCommand", payload, timeout=30)

        # 80001 is the cloud reporting that the device did not answer in time.
        # It means "not delivered", not "rejected", and is worth surfacing.
        if result and result.get("code") == 80001:
            raise DreameCloudError("Device did not acknowledge the command (timeout)")

        entries = ((result or {}).get("data") or {}).get("result") or []
        for entry in entries:
            if entry.get("siid") == siid and entry.get("piid") == piid:
                return entry.get("code") == 0
        return False
