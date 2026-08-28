"""Read-only client for Riot's local + regional (glz/pd) APIs."""

from __future__ import annotations

import base64
import json
import os
import re
import urllib3
from dataclasses import dataclass
from pathlib import Path

import requests

from .lockfile import Lockfile, read_lockfile

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Standard client platform blob every Valorant client sends.
CLIENT_PLATFORM = base64.b64encode(
    json.dumps(
        {
            "platformType": "PC",
            "platformOS": "Windows",
            "platformOSVersion": "10.0.19042.1.256.64bit",
            "platformChipset": "Unknown",
        },
        indent=4,
    ).encode()
).decode()

# Regions that do not have a shard of the same name.
REGION_TO_SHARD = {
    "latam": "na",
    "br": "na",
    "pbe": "pbe",
}

LOG_PATH = "VALORANT/Saved/Logs/ShooterGame.log"


class ClientError(RuntimeError):
    pass


@dataclass
class Auth:
    access_token: str
    entitlements_token: str
    puuid: str


def _log_file() -> Path | None:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None
    path = Path(local_appdata) / LOG_PATH
    return path if path.is_file() else None


def _read_log() -> str:
    path = _log_file()
    if path is None:
        raise ClientError(
            "Could not find ShooterGame.log - launch VALORANT at least once."
        )
    return path.read_text(encoding="utf-8", errors="ignore")


class ValorantClient:
    def __init__(self, lockfile: Lockfile | None = None):
        self.lockfile = lockfile or read_lockfile()
        self.session = requests.Session()
        self.session.verify = False
        self._auth: Auth | None = None
        self._region: str | None = None
        self._shard: str | None = None
        self._client_version: str | None = None
        self._name_cache: dict[str, str] = {}

    # -- local API ---------------------------------------------------------

    def local_get(self, path: str) -> dict:
        url = f"{self.lockfile.base_url}{path}"
        try:
            resp = self.session.get(
                url, auth=self.lockfile.basic_auth, timeout=10
            )
        except requests.RequestException as exc:
            raise ClientError(f"Local API request failed: {exc}") from exc
        if resp.status_code != 200:
            raise ClientError(f"Local API {path} returned {resp.status_code}")
        return resp.json()

    @property
    def auth(self) -> Auth:
        if self._auth is None:
            data = self.local_get("/entitlements/v1/token")
            try:
                self._auth = Auth(
                    access_token=data["accessToken"],
                    entitlements_token=data["token"],
                    puuid=data["subject"],
                )
            except KeyError as exc:
                raise ClientError(
                    "Entitlements response missing field "
                    f"{exc} - is VALORANT signed in?"
                ) from exc
        return self._auth

    # -- region / version --------------------------------------------------

    def _resolve_region(self) -> None:
        # The game log records the glz host it connected to, which carries
        # both region and shard.
        try:
            match = re.search(
                r"https?://glz-([a-z0-9\-]+)-1\.([a-z0-9]+)\.a\.pvp\.net", _read_log()
            )
        except ClientError:
            match = None

        if match:
            self._region, self._shard = match.group(1), match.group(2)
            return

        # Fall back to the Riot Client's own region setting.
        data = self.local_get("/riotclient/region-locale")
        region = str(data.get("region", "")).lower()
        if not region:
            raise ClientError("Could not determine region from the Riot Client.")
        self._region = region
        self._shard = REGION_TO_SHARD.get(region, region)

    @property
    def region(self) -> str:
        if self._region is None:
            self._resolve_region()
        return self._region  # type: ignore[return-value]

    @property
    def shard(self) -> str:
        if self._shard is None:
            self._resolve_region()
        return self._shard  # type: ignore[return-value]

    @property
    def client_version(self) -> str:
        if self._client_version is not None:
            return self._client_version

        override = os.environ.get("VALINFO_CLIENT_VERSION")
        if override:
            self._client_version = override
            return override

        match = re.search(r"CI server version:\s*(\S+)", _read_log())
        if not match:
            raise ClientError(
                "Could not read the client version from ShooterGame.log. "
                "Set VALINFO_CLIENT_VERSION to override."
            )
        parts = match.group(1).strip().split("-")
        # Headers want branch-x.y-shipping-build-rev. Older client logs wrote
        # the build number before "shipping", so normalise the order.
        if "shipping" in parts and parts.index("shipping") != 2:
            parts.insert(2, parts.pop(parts.index("shipping")))
        self._client_version = "-".join(parts)
        return self._client_version

    # -- regional APIs -----------------------------------------------------

    @property
    def glz_url(self) -> str:
        return f"https://glz-{self.region}-1.{self.shard}.a.pvp.net"

    @property
    def pd_url(self) -> str:
        return f"https://pd.{self.shard}.a.pvp.net"

    def headers(self) -> dict[str, str]:
        auth = self.auth
        return {
            "Authorization": f"Bearer {auth.access_token}",
            "X-Riot-Entitlements-JWT": auth.entitlements_token,
            "X-Riot-ClientPlatform": CLIENT_PLATFORM,
            "X-Riot-ClientVersion": self.client_version,
        }

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            return self.session.request(
                method, url, headers=self.headers(), timeout=15, **kwargs
            )
        except requests.RequestException as exc:
            raise ClientError(f"Request to {url} failed: {exc}") from exc

    def get_json(self, url: str) -> dict | None:
        """GET a regional endpoint. Returns None on 404 (not in a match)."""
        resp = self.request("GET", url)
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise ClientError(f"{url} returned {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def player_names(self, puuids: list[str]) -> dict[str, str]:
        """Resolve PUUIDs to 'Name#Tag' via Riot's name service.

        Results are cached, so the live monitor only asks about players it
        has not seen before.
        """
        missing = [p for p in puuids if p not in self._name_cache]
        if missing:
            resp = self.request(
                "PUT", f"{self.pd_url}/name-service/v2/players", json=missing
            )
            if resp.status_code == 200:
                for entry in resp.json():
                    name = entry.get("GameName") or ""
                    tag = entry.get("TagLine") or ""
                    # An empty name means the player hides their Riot ID.
                    self._name_cache[entry["Subject"]] = (
                        f"{name}#{tag}" if name else ""
                    )
        return {p: self._name_cache[p] for p in puuids if p in self._name_cache}
