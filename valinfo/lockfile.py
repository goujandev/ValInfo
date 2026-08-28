"""Read the Riot Client lockfile: local API port + password."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class LockfileError(RuntimeError):
    pass


@dataclass(frozen=True)
class Lockfile:
    name: str
    pid: int
    port: int
    password: str
    protocol: str

    @property
    def base_url(self) -> str:
        return f"{self.protocol}://127.0.0.1:{self.port}"

    @property
    def basic_auth(self) -> tuple[str, str]:
        return ("riot", self.password)


def lockfile_path() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise LockfileError("LOCALAPPDATA is not set - this tool only runs on Windows.")
    return Path(local_appdata) / "Riot Games" / "Riot Client" / "Config" / "lockfile"


def read_lockfile(path: Path | None = None) -> Lockfile:
    path = path or lockfile_path()
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise LockfileError(
            f"Lockfile not found at {path}. Is the Riot Client running?"
        ) from None

    parts = raw.split(":")
    if len(parts) != 5:
        raise LockfileError(f"Unexpected lockfile format: {raw!r}")

    name, pid, port, password, protocol = parts
    return Lockfile(
        name=name,
        pid=int(pid),
        port=int(port),
        password=password,
        protocol=protocol,
    )
