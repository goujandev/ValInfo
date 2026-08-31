"""Tkinter desktop window: the same live match info, as an app."""

from __future__ import annotations

import queue
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import font as tkfont

from . import source
from .content import agent_name, map_name, mode_name, pod_name
from .match import MatchInfo, Player
from .source import MatchSource, State

# Palette. Valorant's red and teal against a near-black chrome.
BG = "#0f1419"
PANEL = "#161c23"
ROW = "#1b222a"
ROW_YOU = "#232c36"
LINE = "#262f39"
RED = "#ff4655"
TEAL = "#18e9d2"
CREAM = "#ece8e1"
GREY = "#8b949e"
DIM = "#5c666f"

# Badge backgrounds: each accent sunk into the panel colour.
RED_TINT = "#31262c"
TEAL_TINT = "#16352f"
GREY_TINT = "#1f262e"

# Status dot (bright, dark) pulse pairs, keyed by what the app is doing.
DOT = {
    "live": (TEAL, "#0d4a42"),
    "idle": (GREY, "#39424b"),
    "down": (RED, "#4a1c22"),
}

PAD = 16


def icon_path() -> Path:
    """The .ico, whether we are running from source or from the bundled exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / "valinfo.ico"


def _font(size: int, weight: str = "normal", family: str = "Segoe UI"):
    return tkfont.Font(family=family, size=size, weight=weight)


def _draw_v(canvas: tk.Canvas, size: int, colour: str) -> None:
    """The angular V mark, scaled to a square canvas of the given size."""
    s = size / 30
    width = max(2, round(5 * s))
    canvas.create_line(5 * s, 6 * s, 15 * s, 25 * s, fill=colour, width=width,
                       capstyle="projecting")
    canvas.create_line(15 * s, 25 * s, 25 * s, 6 * s, fill=colour, width=width,
                       capstyle="projecting")
    canvas.create_rectangle(12 * s, 9 * s, 18 * s, 12 * s, fill=colour,
                            outline=colour)


class PlayerRow(tk.Frame):
    """One player: accent bar, agent, Riot ID."""

    def __init__(self, parent, fonts):
        super().__init__(parent, bg=ROW)
        self.bar = tk.Frame(self, bg=LINE, width=3)
        self.bar.pack(side="left", fill="y")
        self.agent = tk.Label(
            self, bg=ROW, fg=CREAM, font=fonts["agent"], anchor="w", width=12
        )
        self.agent.pack(side="left", padx=(10, 0), pady=7)
        self.name = tk.Label(
            self, bg=ROW, fg=GREY, font=fonts["name"], anchor="w"
        )
        self.name.pack(side="left", padx=(8, 10), pady=7, fill="x", expand=True)

    def update_player(self, player: Player, ally: bool) -> None:
        if not player.agent_id:
            agent, colour = "picking…", DIM
        elif not player.locked:
            # Hovering an agent, not committed to it yet.
            agent, colour = f"○ {agent_name(player.agent_id)}", DIM
        else:
            agent, colour = agent_name(player.agent_id), TEAL if ally else RED

        background = ROW_YOU if player.is_you else ROW
        self.configure(bg=background)
        self.bar.configure(bg=CREAM if player.is_you else (TEAL if ally else RED))
        self.agent.configure(text=agent, fg=colour, bg=background)

        if player.is_you:
            self.name.configure(
                text=player.name or "you", fg=CREAM, bg=background
            )
        elif player.name:
            self.name.configure(text=player.name, fg=GREY, bg=background)
        else:
            # Riot returns an empty name for players who hide their Riot ID.
            self.name.configure(text="hidden", fg=DIM, bg=background)


class Roster(tk.Frame):
    """A team header plus its player rows."""

    def __init__(self, parent, fonts, title: str, colour: str):
        super().__init__(parent, bg=BG)
        self.fonts = fonts
        self.colour = colour
        self.title = title
        self.header = tk.Label(
            self, text=title, bg=BG, fg=colour, font=fonts["section"], anchor="w"
        )
        self.header.pack(fill="x", pady=(0, 6))
        self.empty = tk.Label(
            self,
            text="hidden until the match starts",
            bg=BG,
            fg=DIM,
            font=fonts["small"],
            anchor="w",
        )
        self.rows: list[PlayerRow] = []

    def hide(self) -> None:
        self.pack_forget()

    def show(self, players: list[Player], ally: bool, phase: str) -> None:
        if not players:
            self.header.configure(text=self.title)
        elif phase == "pregame":
            locked = sum(1 for p in players if p.agent_id and p.locked)
            self.header.configure(
                text=f"{self.title}  ·  {locked}/{len(players)} LOCKED"
            )
        else:
            self.header.configure(text=f"{self.title}  ({len(players)})")

        while len(self.rows) < len(players):
            row = PlayerRow(self, self.fonts)
            self.rows.append(row)
        for index, row in enumerate(self.rows):
            if index < len(players):
                row.update_player(players[index], ally)
                row.pack(fill="x", pady=1)
            else:
                row.pack_forget()

        if players:
            self.empty.pack_forget()
        else:
            self.empty.pack(fill="x", pady=2)


class ValInfoApp(tk.Tk):
    def __init__(self, resolve_names: bool = True):
        super().__init__()
        self.title("ValInfo")
        self.configure(bg=BG)
        self.geometry("470x690")
        self.minsize(430, 560)

        self.fonts = {
            "logo": _font(13, "bold"),
            "map": _font(23, "bold"),
            "label": _font(8, "bold"),
            "value": _font(11),
            "section": _font(9, "bold"),
            "agent": _font(10, "bold"),
            "name": _font(10),
            "small": _font(9),
            "badge": _font(8, "bold"),
            "idle": _font(15, "bold"),
        }

        self._signature: object = None
        self._pulse = 0
        self._dot_key = "idle"
        self._queue: queue.Queue[State] = queue.Queue()
        self._stop = threading.Event()

        self._build()
        self._apply_chrome()
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._feed = MatchSource(resolve_names=resolve_names)
        self._worker = threading.Thread(target=self._poll_loop, daemon=True)
        self._worker.start()
        self.after(100, self._drain)
        self.after(500, self._pulse_dot)

    # -- layout ------------------------------------------------------------

    def _build(self) -> None:
        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x")
        tk.Frame(self, bg=LINE, height=1).pack(fill="x")

        logo = tk.Canvas(
            header, width=30, height=30, bg=PANEL, highlightthickness=0
        )
        _draw_v(logo, 30, RED)
        logo.pack(side="left", padx=(PAD, 8), pady=12)

        tk.Label(
            header, text="VALINFO", bg=PANEL, fg=CREAM, font=self.fonts["logo"]
        ).pack(side="left")

        self.pin = tk.Label(
            header,
            text="PIN",
            bg=PANEL,
            fg=DIM,
            font=self.fonts["badge"],
            cursor="hand2",
            padx=8,
            pady=4,
        )
        self.pin.pack(side="right", padx=(0, PAD))
        self.pin.bind("<Button-1>", self.toggle_pin)
        self.pin.bind("<Enter>", lambda _e: self._paint_pin(hover=True))
        self.pin.bind("<Leave>", lambda _e: self._paint_pin(hover=False))
        self._pinned = False

        self.phase = tk.Label(
            header, text="", bg=PANEL, fg=GREY, font=self.fonts["badge"],
            padx=8, pady=3,
        )
        self.phase.pack(side="right", padx=8)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # The two body views: live match details, and an idle placeholder.
        # Exactly one is packed at a time.
        self.match_view = tk.Frame(body, bg=BG)
        self.idle_view = tk.Frame(body, bg=BG)

        view = self.match_view
        self.map_label = tk.Label(
            view, text="—", bg=BG, fg=CREAM, font=self.fonts["map"], anchor="w"
        )
        self.map_label.pack(fill="x")

        facts = tk.Frame(view, bg=BG)
        facts.pack(fill="x", pady=(8, 14))
        self.mode_value = self._fact(facts, "MODE", 0)
        self.server_value = self._fact(facts, "SERVER", 1)
        self.side_value = self._fact(facts, "SIDE", 2)
        for column in range(3):
            facts.columnconfigure(column, weight=1)

        tk.Frame(view, bg=LINE, height=1).pack(fill="x", pady=(0, 14))

        self.allies = Roster(view, self.fonts, "YOUR TEAM", TEAL)
        self.spacer = tk.Frame(view, bg=BG, height=14)
        self.enemies = Roster(view, self.fonts, "ENEMY TEAM", RED)

        centre = tk.Frame(self.idle_view, bg=BG)
        centre.pack(expand=True)
        mark = tk.Canvas(centre, width=64, height=64, bg=BG, highlightthickness=0)
        _draw_v(mark, 64, "#55323a")
        mark.pack(pady=(0, 14))
        self.idle_headline = tk.Label(
            centre, text="", bg=BG, fg=CREAM, font=self.fonts["idle"]
        )
        self.idle_headline.pack()
        self.idle_detail = tk.Label(
            centre, text="", bg=BG, fg=GREY, font=self.fonts["small"],
            justify="center", wraplength=360,
        )
        self.idle_detail.pack(pady=(6, 0))

        footer = tk.Frame(self, bg=PANEL)
        footer.pack(fill="x", side="bottom")
        tk.Frame(self, bg=LINE, height=1).pack(fill="x", side="bottom")
        self.dot = tk.Canvas(
            footer, width=8, height=8, bg=PANEL, highlightthickness=0
        )
        self.dot_id = self.dot.create_oval(0, 0, 7, 7, fill=GREY, outline="")
        self.dot.pack(side="left", padx=(PAD, 6), pady=9)
        self.status = tk.Label(
            footer, text="starting…", bg=PANEL, fg=DIM, font=self.fonts["small"]
        )
        self.status.pack(side="left")

    def _apply_chrome(self) -> None:
        """Dark title bar and the app icon - both best-effort."""
        self.update_idletasks()
        try:
            import ctypes

            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            value = ctypes.c_int(1)
            for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)
                ) == 0:
                    break
        except Exception:
            pass

        try:
            self.iconbitmap(str(icon_path()))
        except Exception:
            pass

    def _fact(self, parent: tk.Frame, label: str, column: int) -> tk.Label:
        cell = tk.Frame(parent, bg=BG)
        cell.grid(row=0, column=column, sticky="ew", padx=(0, 8))
        tk.Label(
            cell, text=label, bg=BG, fg=DIM, font=self.fonts["label"], anchor="w"
        ).pack(fill="x")
        value = tk.Label(
            cell, text="—", bg=BG, fg=CREAM, font=self.fonts["value"], anchor="w"
        )
        value.pack(fill="x")
        return value

    # -- behaviour ---------------------------------------------------------

    def toggle_pin(self, _event=None) -> None:
        self._pinned = not self._pinned
        self.attributes("-topmost", self._pinned)
        self._paint_pin(hover=True)

    def _paint_pin(self, hover: bool) -> None:
        if self._pinned:
            self.pin.configure(fg=RED, bg=RED_TINT)
        else:
            self.pin.configure(fg=GREY if hover else DIM, bg=PANEL)

    def _badge(self, text: str, colour: str, tint: str) -> None:
        self.phase.configure(text=text, fg=colour, bg=tint)

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                state = self._feed.poll()
            except Exception as exc:  # never let the worker die
                state = State(source.ERROR, message="Something went wrong.",
                              detail=str(exc))
            self._queue.put(state)
            # Sleep in slices so closing the window feels instant.
            deadline = time.monotonic() + state.interval
            while time.monotonic() < deadline and not self._stop.is_set():
                time.sleep(0.1)

    def _drain(self) -> None:
        state = None
        while True:
            try:
                state = self._queue.get_nowait()
            except queue.Empty:
                break
        if state is not None:
            self._apply(state)
        self.after(100, self._drain)

    def _pulse_dot(self) -> None:
        self._pulse ^= 1
        bright, dark = DOT[self._dot_key]
        self.dot.itemconfigure(self.dot_id, fill=bright if self._pulse else dark)
        self.after(700, self._pulse_dot)

    def _apply(self, state: State) -> None:
        if state.kind == source.MATCH and state.info is not None:
            self._show_match(state.info)
            self._dot_key = "live"
            self.status.configure(
                text=f"live · updated {time.strftime('%H:%M:%S')}"
            )
            return

        self._signature = None
        labels = {
            source.STANDBY: ("STANDBY", GREY, "Not in a match", "idle"),
            source.NO_CLIENT: ("WAITING", GREY, "No Riot Client", "down"),
            source.ERROR: ("RETRYING", RED, "Reconnecting", "down"),
        }
        badge, colour, headline, dot = labels.get(
            state.kind, ("WAITING", GREY, "Waiting", "idle")
        )
        self._badge(badge, colour, RED_TINT if colour == RED else GREY_TINT)
        self._dot_key = dot
        self.title("ValInfo")

        self.match_view.pack_forget()
        self.idle_view.pack(fill="both", expand=True, padx=PAD, pady=PAD)
        self.idle_headline.configure(text=headline)
        self.idle_detail.configure(text=state.detail)
        self.status.configure(text=f"watching · checked {time.strftime('%H:%M:%S')}")

    def _show_match(self, info: MatchInfo) -> None:
        # Only touch the widgets when something actually changed.
        signature = (
            info.match_id,
            info.phase,
            info.map_id,
            info.mode_id,
            info.pod_id,
            info.your_team,
            tuple((p.puuid, p.agent_id, p.locked, p.name) for p in info.players),
        )
        if signature == self._signature:
            return
        self._signature = signature

        ally_colour = TEAL if info.your_team == "Blue" else RED
        self._badge(
            "AGENT SELECT" if info.phase == "pregame" else "IN GAME",
            ally_colour,
            TEAL_TINT if ally_colour == TEAL else RED_TINT,
        )
        self.title(f"ValInfo · {map_name(info.map_id)}")

        self.idle_view.pack_forget()
        self.match_view.pack(fill="both", expand=True, padx=PAD, pady=(PAD, 0))
        self.map_label.configure(text=map_name(info.map_id), fg=CREAM)
        self.mode_value.configure(text=mode_name(info.mode_id))
        self.server_value.configure(text=pod_name(info.pod_id))
        self.side_value.configure(text=info.side, fg=ally_colour)
        self.allies.pack(fill="x")
        self.spacer.pack(fill="x")
        self.enemies.pack(fill="x")
        self.allies.show(
            sorted(info.allies, key=lambda p: not p.is_you), True, info.phase
        )
        self.enemies.show(info.enemies, False, info.phase)

    def close(self) -> None:
        self._stop.set()
        self.destroy()


def run(resolve_names: bool = True) -> int:
    app = ValInfoApp(resolve_names=resolve_names)
    app.mainloop()
    return 0
