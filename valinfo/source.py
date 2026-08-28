"""Polling logic shared by the terminal monitor and the GUI."""

from __future__ import annotations

from dataclasses import dataclass

from .client import ClientError, ValorantClient
from .lockfile import LockfileError, read_lockfile
from .match import MatchInfo, current_match

# How often to poll, in seconds. Agent select moves fast, so it gets a
# tighter loop than "nothing is happening".
IDLE_INTERVAL = 3.0
MATCH_INTERVAL = 2.0

MATCH = "match"
STANDBY = "standby"
NO_CLIENT = "no_client"
ERROR = "error"


@dataclass
class State:
    kind: str
    info: MatchInfo | None = None
    message: str = ""
    detail: str = ""
    restarted: bool = False

    @property
    def interval(self) -> float:
        return MATCH_INTERVAL if self.kind == MATCH else IDLE_INTERVAL


class MatchSource:
    """Keeps a client alive across polls and reports the current state."""

    def __init__(self, resolve_names: bool = True):
        self.resolve_names = resolve_names
        self.client: ValorantClient | None = None

    def poll(self) -> State:
        try:
            lock = read_lockfile()
        except LockfileError:
            self.client = None
            return State(
                NO_CLIENT,
                message="Waiting for the Riot Client.",
                detail="Start VALORANT - this picks it up automatically.",
            )

        restarted = False
        # The port and password change whenever the Riot Client restarts.
        if (
            self.client is None
            or self.client.lockfile.port != lock.port
            or self.client.lockfile.password != lock.password
        ):
            self.client = ValorantClient(lock)
            restarted = True

        try:
            info = current_match(self.client, resolve_names=self.resolve_names)
        except ClientError as exc:
            # Transient: the client refuses requests while it is loading.
            return State(
                ERROR,
                message="Reconnecting to the client.",
                detail=str(exc),
                restarted=restarted,
            )

        if info is None:
            return State(
                STANDBY,
                message="Not in a match.",
                detail="Queue up - this fills in the moment agent select starts.",
                restarted=restarted,
            )
        return State(MATCH, info=info, restarted=restarted)
