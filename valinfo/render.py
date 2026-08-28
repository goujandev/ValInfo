"""Neofetch-style rendering: logo, colors, and animation."""

from __future__ import annotations

import os
import sys
import time

from .content import agent_name, map_name, pod_name
from .match import MatchInfo, Player

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Valorant's palette.
RED = (255, 70, 85)
TEAL = (24, 233, 210)
BLUE = (86, 156, 255)
CREAM = (236, 232, 225)
GREY = (130, 128, 130)
DARK = (52, 52, 58)

LOGO = [
    "▐█▌                 ▐█▌",
    " ▐█▌               ▐█▌ ",
    "  ▐█▌   ▄▄▄▄▄▄▄   ▐█▌  ",
    "   ▐█▌  ▀▀▀▀▀▀▀  ▐█▌   ",
    "    ▐█▌         ▐█▌    ",
    "     ▐█▌       ▐█▌     ",
    "      ▐█▌     ▐█▌      ",
    "       ▐█▌   ▐█▌       ",
    "        ▐█▌ ▐█▌        ",
    "         ▐███▌         ",
]

ASCII_LOGO = [
    "|#|                 |#|",
    " |#|               |#| ",
    "  |#|   =======   |#|  ",
    "   |#|  =======  |#|   ",
    "    |#|         |#|    ",
    "     |#|       |#|     ",
    "      |#|     |#|      ",
    "       |#|   |#|       ",
    "        |#| |#|        ",
    "         |###|         ",
]

UNICODE = {
    "logo": LOGO,
    "rule": "─",
    "bar": "▍",
    "block": "█",
    "spin": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    "ell": "…",
}
ASCII = {
    "logo": ASCII_LOGO,
    "rule": "-",
    "bar": "|",
    "block": "#",
    "spin": "|/-\\",
    "ell": "...",
}

G = UNICODE  # swapped for ASCII when the console cannot cope


def setup_stdout() -> None:
    """Prefer UTF-8 output, then fall back to ASCII art if that fails."""
    global G
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    encoding = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        "▐█▌─▍…".encode(encoding)
        G = UNICODE
    except (UnicodeEncodeError, LookupError):
        G = ASCII


def logo_width() -> int:
    return max(len(line) for line in G["logo"])


def enable_ansi() -> bool:
    """Turn on VT processing so colors work in plain cmd.exe too."""
    if os.name != "nt":
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


class Style:
    """Colour helper that collapses to plain text when colour is off."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def __call__(self, text: str, rgb: tuple[int, int, int] | None = None,
                 bold: bool = False, dim: bool = False) -> str:
        if not self.enabled:
            return text
        prefix = ""
        if rgb:
            prefix += "\033[38;2;{};{};{}m".format(*rgb)
        if bold:
            prefix += BOLD
        if dim:
            prefix += DIM
        return f"{prefix}{text}{RESET}" if prefix else text

    def gradient(self, text: str, start: tuple[int, int, int],
                 end: tuple[int, int, int]) -> str:
        if not self.enabled or not text:
            return text
        out = []
        span = max(len(text) - 1, 1)
        for i, char in enumerate(text):
            r, g, b = (
                int(start[j] + (end[j] - start[j]) * i / span) for j in range(3)
            )
            out.append(f"\033[38;2;{r};{g};{b}m{char}")
        return "".join(out) + RESET


def visible_len(text: str) -> int:
    """Length of a string ignoring ANSI escape sequences."""
    out, i = 0, 0
    while i < len(text):
        if text[i] == "\033":
            while i < len(text) and text[i] != "m":
                i += 1
        else:
            out += 1
        i += 1
    return out


def logo_lines(style: Style) -> list[str]:
    return [style.gradient(line, RED, (150, 30, 60)) for line in G["logo"]]


def side_by_side(logo: list[str], right: list[str]) -> list[str]:
    """Lay the logo out to the left of an info block, neofetch style."""
    width = logo_width()
    rows = []
    for i in range(max(len(logo), len(right))):
        left = logo[i] if i < len(logo) else " " * width
        pad = " " * max(0, width - visible_len(left))
        text = right[i] if i < len(right) else ""
        rows.append(f"  {left}{pad}   {text}".rstrip())
    return rows


def _player_row(player: Player, style: Style, ally: bool) -> str:
    agent = agent_name(player.agent_id)
    if not player.agent_id:
        agent, hue = "picking" + G["ell"], GREY
    elif not player.locked:
        agent, hue = f"{agent} ~", GREY
    else:
        hue = TEAL if ally else RED

    marker = style(G["bar"], CREAM if player.is_you else (40, 40, 44))
    if player.is_you:
        name_out = style(player.name or "you", CREAM, bold=True)
    elif player.name:
        name_out = style(player.name, GREY)
    else:
        # Riot returns an empty name for players who hide their Riot ID.
        name_out = style("hidden", GREY, dim=True)
    pad = " " * max(0, 14 - len(agent))
    return f"{marker} {style(agent, hue, bold=player.is_you)}{pad} {name_out}"


def info_lines(info: MatchInfo, style: Style) -> list[str]:
    you = next((p for p in info.players if p.is_you), None)
    title = you.name if you and you.name else "VALORANT"
    phase = "AGENT SELECT" if info.phase == "pregame" else "IN GAME"
    ally_hue = TEAL if info.your_team == "Blue" else RED

    lines = [
        style(title, CREAM, bold=True) + "  " + style(phase, ally_hue, bold=True),
        style(G["rule"] * 30, DARK),
        style("MAP    ", GREY) + style(map_name(info.map_id), CREAM, bold=True),
        style("SERVER ", GREY) + style(pod_name(info.pod_id), CREAM),
        style("SIDE   ", GREY) + style(info.side, ally_hue, bold=True),
        "",
        style(f"YOUR TEAM ({len(info.allies)})", TEAL, bold=True),
    ]
    lines += [_player_row(p, style, True)
              for p in sorted(info.allies, key=lambda p: not p.is_you)]

    enemies = info.enemies
    lines += ["", style(f"ENEMY TEAM ({len(enemies)})", RED, bold=True)]
    if enemies:
        lines += [_player_row(p, style, False) for p in enemies]
    else:
        lines.append(style("  hidden until the match starts", GREY, dim=True))

    block = G["block"] * 3
    lines += ["", "".join(
        style(block, hue) for hue in (RED, (255, 130, 90), CREAM, TEAL, BLUE)
    )]
    return lines


def compose(info: MatchInfo, style: Style) -> list[str]:
    return side_by_side(logo_lines(style), info_lines(info, style))


def idle(style: Style) -> list[str]:
    right = [
        style("VALORANT", CREAM, bold=True) + "  " + style("STANDBY", GREY, bold=True),
        style(G["rule"] * 30, DARK),
        style("Not in a match.", GREY),
        style("Queue up - this fills in at agent select.", GREY, dim=True),
    ]
    return side_by_side(logo_lines(style), right)


def animate(rows: list[str], delay: float = 0.018) -> None:
    """Reveal the output one line at a time."""
    if delay <= 0:
        print("\n".join(rows))
        return
    try:
        sys.stdout.write(HIDE_CURSOR)
        for row in rows:
            sys.stdout.write(row + "\n")
            sys.stdout.flush()
            time.sleep(delay)
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()


class Spinner:
    """Braille spinner shown while the client is being queried."""

    def __init__(self, label: str, style: Style, enabled: bool = True):
        self.label, self.style, self.enabled = label, style, enabled
        self.frame = 0

    def __enter__(self):
        if self.enabled:
            sys.stdout.write(HIDE_CURSOR)
        return self

    def tick(self) -> None:
        if not self.enabled:
            return
        frames = G["spin"]
        char = frames[self.frame % len(frames)]
        self.frame += 1
        sys.stdout.write(f"\r {self.style(char, RED)} {self.style(self.label, GREY)}")
        sys.stdout.flush()

    def __exit__(self, *exc) -> None:
        if self.enabled:
            sys.stdout.write("\r\033[2K" + SHOW_CURSOR)
            sys.stdout.flush()
