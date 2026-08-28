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
HOMES_PATH = "dreame-user-iot/smarthome/home"
SCENE_LIST_PATH = "dreame-user-iot/smarthome/scene/getSceneByHomeV2"
SCENE_SAVE_PATH = "dreame-user-iot/smarthome/scene/saveOrUpdate"
SCENE_START_PATH = "dreame-user-iot/smarthome/scene/startSceneAction"
SCENE_COMMANDS_PATH = "dreame-user-iot/smarthome/scene/action/getDeviceCommand"

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

    def _get(self, path: str, params: dict | None = None) -> Any:
        """GET flavour of :meth:`_call`.

        The scene endpoints are split across both verbs - listing is a GET and
        answers ``10002 不支持当前请求方法`` ("request method not supported") to a
        POST, which is easy to mistake for a bad payload.
        """
        if not self._access_token or time.time() > self._expires_at:
            self.login()
        headers = self._auth_headers()
        headers["Dreame-Auth"] = self._access_token
        try:
            response = self._session.get(
                f"{self.api_url}/{path}", headers=headers, params=params,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.RequestException as err:
            raise DreameCloudError(f"Request to {path} failed: {err}") from err
        if response.status_code == 401:
            self._access_token = None
            self.login()
            return self._get(path, params)
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


    # --- scenes: the only way to switch this fan's power ---------------------
    # The device refuses every write to 2.1 through the RPC (80001, "device did
    # not acknowledge"), whether it is running or not, while accepting writes to
    # every other property in the same session. The vendor's app does not use
    # that path for power: it stores an "on" or "off" action in a scene and asks
    # the cloud to run it. That works, from a stopped fan, in about five seconds.

    def get_homes(self) -> list[dict]:
        """Homes on the account; scenes hang off a home, not off a device."""
        result = self._get(HOMES_PATH)
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Home list failed: {result}")
        return result["data"]["homes"]

    def get_scenes(self, home_id: str) -> list[dict]:
        """Every scene of a home, manual and automatic alike."""
        result = self._get(SCENE_LIST_PATH, {"homeId": home_id})
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Scene list failed: {result}")
        data = result.get("data") or {}
        return (data.get("manual") or []) + (data.get("auto") or [])

    def get_scene_commands(self, did: str, model: str) -> list[dict]:
        """What the cloud says this device can be told to do inside a scene."""
        result = self._call(SCENE_COMMANDS_PATH, {"did": str(did), "model": model})
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Scene command list failed: {result}")
        return result.get("data") or []

    def create_manual_scene(
        self, home_id: str, name: str, did: str, model: str,
        command_id: str, value: str, action_name: str = "",
    ) -> None:
        """Create a manually-triggered scene holding one device command.

        The whole scene goes in one payload. ``saveCommandAction`` looks like
        the endpoint for this and answers ``code: 0`` to anything, storing
        nothing - the action has to ride along here, and its key is ``id``,
        not ``commandId``.
        """
        payload = {
            "homeId": str(home_id),
            "sceneName": name,
            "triggerType": "all",
            "triggerData": [{"dataType": "manual", "detail": []}],
            "deviceInfo": [{
                "did": str(did),
                "model": model,
                "actionName": action_name or name,
                "detail": [{"id": str(command_id), "detailType": "enum", "value": str(value)}],
            }],
            "dateType": "daily",
        }
        result = self._call(SCENE_SAVE_PATH, payload)
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Scene create failed: {result}")

    def start_scene(self, scene_id: str) -> None:
        """Run a scene's actions now."""
        result = self._call(SCENE_START_PATH, {"sceneId": str(scene_id)})
        if not result or result.get("code") != 0:
            raise DreameCloudError(f"Scene start failed: {result}")
