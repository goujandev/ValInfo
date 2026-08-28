"""Static ID -> human-readable name mappings (public game constants)."""

from __future__ import annotations

AGENTS: dict[str, str] = {
    "41fb69c1-4189-7b37-f117-bcaf1e96f1bf": "Astra",
    "5f8d3a7f-467b-97f3-062c-13acf203c006": "Breach",
    "9f0d8ba9-4140-b941-57d3-a7ad57c6b417": "Brimstone",
    "22697a3d-45bf-8dd7-4fec-84a9e28c69d7": "Chamber",
    "1dbf2edd-4729-0984-3115-daa5eed44993": "Clove",
    "117ed9e3-49f3-6512-3ccf-0cada7e3823b": "Cypher",
    "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235": "Deadlock",
    "dade69b4-4f5a-8528-247b-219e5a1facd6": "Fade",
    "e370fa57-4757-3604-3648-499e1f642d3f": "Gekko",
    "95b78ed7-4637-86d9-7e41-71ba8c293152": "Harbor",
    "0e38b510-41a8-5780-5e8f-568b2a4f2d6c": "Iso",
    "add6443a-41bd-e414-f6ad-e58d267f4e95": "Jett",
    "601dbbe7-43ce-be57-2a40-4abd24953621": "KAY/O",
    "1e58de9c-4950-5125-93e9-a0aee9f98746": "Killjoy",
    "bb2a4828-46eb-8cd1-e765-15848195d751": "Neon",
    "8e253930-4c05-31dd-1b6c-968525494517": "Omen",
    "eb93336a-449b-9c1b-0a54-a891f7921d69": "Phoenix",
    "f94c3b30-42be-e959-889c-5aa313dba261": "Raze",
    "a3bfb853-43b2-7238-a4f1-ad90e9e46bcc": "Reyna",
    "569fdd95-4d10-43ab-ca70-79becc718b46": "Sage",
    "6f2a04ca-43e0-be17-7f36-b3908627744d": "Skye",
    "320b2a48-4d9b-a075-30f1-1f93a9b638fa": "Sova",
    "b444168c-4e35-8076-db47-ef9bf368f384": "Tejo",
    "707eab51-4836-f488-046a-cda6bf494859": "Viper",
    "efba5359-4016-a1e5-7626-b1ae76895940": "Vyse",
    "df1cb487-4902-002e-5c17-d28e83e78588": "Waylay",
    "7f94d92c-4234-0a36-9646-3a87eb8b5c89": "Yoru",
}

MAPS: dict[str, str] = {
    "/Game/Maps/Ascent/Ascent": "Ascent",
    "/Game/Maps/Bonsai/Bonsai": "Split",
    "/Game/Maps/Canyon/Canyon": "Fracture",
    "/Game/Maps/Duality/Duality": "Bind",
    "/Game/Maps/Foxtrot/Foxtrot": "Breeze",
    "/Game/Maps/Infinity/Infinity": "Abyss",
    "/Game/Maps/Jam/Jam": "Lotus",
    "/Game/Maps/Juliett/Juliett": "Sunset",
    "/Game/Maps/Pitt/Pitt": "Pearl",
    "/Game/Maps/Port/Port": "Icebox",
    "/Game/Maps/Rook/Rook": "Corrode",
    "/Game/Maps/Triad/Triad": "Haven",
    "/Game/Maps/HURM/HURM_Alley": "District",
    "/Game/Maps/HURM/HURM_Bowl": "Kasbah",
    "/Game/Maps/HURM/HURM_Helix": "Drift",
    "/Game/Maps/HURM/HURM_HighTide": "Glitch",
    "/Game/Maps/HURM/HURM_Yard": "Piazza",
    "/Game/Maps/Poveglia/Range": "The Range",
}

MODES: dict[str, str] = {
    "/game/gamemodes/bomb/bombgamemode.bombgamemode": "Standard",
    "/game/gamemodes/deathmatch/deathmatchgamemode.deathmatchgamemode": "Deathmatch",
    "/game/gamemodes/ggteam/ggteamgamemode.ggteamgamemode": "Escalation",
    "/game/gamemodes/hurm/hurmgamemode.hurmgamemode": "Team Deathmatch",
    "/game/gamemodes/newmap/newmapgamemode.newmapgamemode": "New Map",
    "/game/gamemodes/onefa/onefagamemode.onefagamemode": "Replication",
    "/game/gamemodes/quickbomb/quickbombgamemode.quickbombgamemode": "Spike Rush",
    "/game/gamemodes/swiftplay/swiftplaygamemode.swiftplaygamemode": "Swiftplay",
    "/game/gamemodes/snowballfight/snowballfightgamemode.snowballfightgamemode": "Snowball Fight",
}

# Game pod suffix (last component of the pod ID, minus the trailing index)
# -> human-readable datacenter location.
PODS: dict[str, str] = {
    "na-gp-ashburn": "Ashburn, VA",
    "na-gp-atlanta": "Atlanta, GA",
    "na-gp-chicago": "Chicago, IL",
    "na-gp-dallas": "Dallas, TX",
    "na-gp-illinois": "Illinois",
    "na-gp-losangeles": "Los Angeles, CA",
    "na-gp-miami": "Miami, FL",
    "na-gp-oregon": "Oregon",
    "na-gp-portland": "Portland, OR",
    "na-gp-sterling": "Sterling, VA",
    "na-gp-texas": "Texas",
    "us-boston": "Boston, MA",
    "us-central": "Central US",
    "us-east": "US East",
    "us-west": "US West",
    "latam-gp-mexicocity": "Mexico City",
    "latam-gp-santiago": "Santiago",
    "br-gp-saopaulo": "Sao Paulo",
    "eu-gp-amsterdam": "Amsterdam",
    "eu-gp-bahrain": "Bahrain",
    "eu-gp-frankfurt": "Frankfurt",
    "eu-gp-london": "London",
    "eu-gp-madrid": "Madrid",
    "eu-gp-milan": "Milan",
    "eu-gp-paris": "Paris",
    "eu-gp-stockholm": "Stockholm",
    "eu-gp-warsaw": "Warsaw",
    "eu-gp-istanbul": "Istanbul",
    "ap-gp-hongkong": "Hong Kong",
    "ap-gp-mumbai": "Mumbai",
    "ap-gp-seoul": "Seoul",
    "ap-gp-singapore": "Singapore",
    "ap-gp-sydney": "Sydney",
    "ap-gp-tokyo": "Tokyo",
    "ap-gp-taipei": "Taipei",
    "ap-gp-jakarta": "Jakarta",
    "kr-gp-seoul": "Seoul",
}


def agent_name(agent_id: str | None) -> str:
    if not agent_id:
        return "(none)"
    return AGENTS.get(agent_id.lower(), f"Unknown ({agent_id[:8]})")


def map_name(map_id: str | None) -> str:
    if not map_id:
        return "Unknown map"
    for path, name in MAPS.items():
        if path.lower() == map_id.lower():
            return name
    return map_id.rstrip("/").rsplit("/", 1)[-1] or "Unknown map"


def mode_name(mode_id: str | None) -> str:
    if not mode_id:
        return "Unknown mode"
    return MODES.get(mode_id.lower(), mode_id.rstrip("/").rsplit("/", 1)[-1])


def pod_name(pod_id: str | None) -> str:
    """'aresriot.aws-rclusterprod-use1-1.na-gp-ashburn-1' -> 'Ashburn, VA'."""
    if not pod_id:
        return "Unknown server"

    tail = pod_id.split(".")[-1].lower()
    key = tail.rsplit("-", 1)[0] if tail.rsplit("-", 1)[-1].isdigit() else tail
    if key in PODS:
        return PODS[key]

    # Fall back to prettifying the pod id: drop region prefix and 'gp' marker.
    parts = [p for p in key.split("-") if p not in ("gp",)]
    if len(parts) > 1:
        parts = parts[1:]
    return " ".join(p.capitalize() for p in parts) or pod_id
