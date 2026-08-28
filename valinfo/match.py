"""Fetch and normalise pregame / core-game state."""

from __future__ import annotations

from dataclasses import dataclass, field

from .client import ValorantClient

# First-half sides. Blue starts on defense, Red on attack.
SIDES = {"Blue": "Defenders", "Red": "Attackers"}


@dataclass
class Player:
    puuid: str
    team: str
    agent_id: str | None
    is_you: bool = False
    locked: bool = True
    name: str = ""


@dataclass
class MatchInfo:
    phase: str  # "pregame" or "ingame"
    match_id: str
    map_id: str | None
    mode_id: str | None
    pod_id: str | None
    your_team: str
    players: list[Player] = field(default_factory=list)

    @property
    def side(self) -> str:
        return SIDES.get(self.your_team, self.your_team or "Unknown")

    def team(self, team_id: str) -> list[Player]:
        return [p for p in self.players if p.team == team_id]

    @property
    def allies(self) -> list[Player]:
        return self.team(self.your_team)

    @property
    def enemies(self) -> list[Player]:
        return [p for p in self.players if p.team != self.your_team]


def _pregame(client: ValorantClient, puuid: str) -> MatchInfo | None:
    player = client.get_json(f"{client.glz_url}/pregame/v1/players/{puuid}")
    if not player:
        return None
    match_id = player["MatchID"]

    data = client.get_json(f"{client.glz_url}/pregame/v1/matches/{match_id}")
    if not data:
        return None

    players: list[Player] = []
    your_team = ""
    for team in (data.get("AllyTeam"), data.get("EnemyTeam")):
        if not team:
            continue
        team_id = team.get("TeamID", "")
        for entry in team.get("Players", []):
            is_you = entry["Subject"] == puuid
            if is_you:
                your_team = team_id
            state = entry.get("CharacterSelectionState", "")
            players.append(
                Player(
                    puuid=entry["Subject"],
                    team=team_id,
                    agent_id=entry.get("CharacterID") or None,
                    is_you=is_you,
                    locked=state == "locked",
                )
            )

    return MatchInfo(
        phase="pregame",
        match_id=match_id,
        map_id=data.get("MapID"),
        mode_id=data.get("ModeID"),
        pod_id=data.get("GamePodID"),
        your_team=your_team or (data.get("AllyTeam") or {}).get("TeamID", ""),
        players=players,
    )


def _coregame(client: ValorantClient, puuid: str) -> MatchInfo | None:
    player = client.get_json(f"{client.glz_url}/core-game/v1/players/{puuid}")
    if not player:
        return None
    match_id = player["MatchID"]

    data = client.get_json(f"{client.glz_url}/core-game/v1/matches/{match_id}")
    if not data:
        return None

    players: list[Player] = []
    your_team = ""
    for entry in data.get("Players", []):
        if entry.get("IsCoach"):
            continue
        is_you = entry["Subject"] == puuid
        if is_you:
            your_team = entry.get("TeamID", "")
        players.append(
            Player(
                puuid=entry["Subject"],
                team=entry.get("TeamID", ""),
                agent_id=entry.get("CharacterID") or None,
                is_you=is_you,
            )
        )

    return MatchInfo(
        phase="ingame",
        match_id=match_id,
        map_id=data.get("MapID"),
        mode_id=data.get("ModeID"),
        pod_id=data.get("GamePodID"),
        your_team=your_team,
        players=players,
    )


def current_match(client: ValorantClient, resolve_names: bool = True) -> MatchInfo | None:
    """Return the live match, checking core-game first, then pregame."""
    puuid = client.auth.puuid
    info = _coregame(client, puuid) or _pregame(client, puuid)
    if info is None:
        return None

    if resolve_names:
        names = client.player_names([p.puuid for p in info.players])
        for player in info.players:
            player.name = names.get(player.puuid, "")

    return info
