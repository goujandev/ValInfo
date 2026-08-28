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
from .content import agent_name, map_name, pod_name
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

PAD = 16


def icon_path() -> Path:
    """The .ico, whether we are running from source or from the bundled exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / "valinfo.ico"


def _font(size: int, weight: str = "normal", family: str = "Segoe UI"):
    return tkfont.Font(family=family, size=size, weight=weight)


class PlayerRow(tk.Frame):
    """One player: accent bar, agent, Riot ID."""

    def __init__(self, parent, fonts):
        super().__init__(parent, bg=ROW)
        self.bar = tk.Frame(self, bg=LINE, width=3)
        self.bar.pack(side="left", fill="y")
        self.agent = tk.Label(
            self, bg=ROW, fg=CREAM, font=fonts["agent"], anchor="w", width=12
        )
        self.agent.pack(side="left", padx=(10, 0), pady=6)
        self.name = tk.Label(
            self, bg=ROW, fg=GREY, font=fonts["name"], anchor="w"
        )
        self.name.pack(side="left", padx=(8, 10), pady=6, fill="x", expand=True)

    def update_player(self, player: Player, ally: bool) -> None:
        agent = agent_name(player.agent_id)
        if not player.agent_id:
            agent, colour = "Picking…", DIM
        elif not player.locked:
            agent, colour = f"{agent} ~", DIM
        else:
            colour = TEAL if ally else RED

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

    def show(self, players: list[Player], ally: bool) -> None:
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
        }

        self._signature: object = None
        self._pulse = 0
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

        logo = tk.Canvas(
            header, width=30, height=30, bg=PANEL, highlightthickness=0
        )
        logo.create_line(5, 6, 15, 25, fill=RED, width=5, capstyle="projecting")
        logo.create_line(15, 25, 25, 6, fill=RED, width=5, capstyle="projecting")
        logo.create_rectangle(12, 9, 18, 12, fill=RED, outline=RED)
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
        self._pinned = False

        self.phase = tk.Label(
            header, text="", bg=PANEL, fg=GREY, font=self.fonts["badge"]
        )
        self.phase.pack(side="right", padx=8)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=PAD, pady=(PAD, 0))

        self.map_label = tk.Label(
            body, text="—", bg=BG, fg=CREAM, font=self.fonts["map"], anchor="w"
        )
        self.map_label.pack(fill="x")

        self.detail = tk.Label(
            body, text="", bg=BG, fg=GREY, font=self.fonts["small"],
            anchor="w", justify="left", wraplength=400,
        )
        self.detail.pack(fill="x", pady=(2, 12))

        facts = tk.Frame(body, bg=BG)
        facts.pack(fill="x", pady=(0, 14))
        self.server_value = self._fact(facts, "SERVER", 0)
        self.side_value = self._fact(facts, "SIDE", 1)
        facts.columnconfigure(0, weight=1)
        facts.columnconfigure(1, weight=1)

        tk.Frame(body, bg=LINE, height=1).pack(fill="x", pady=(0, 14))

        self.allies = Roster(body, self.fonts, "YOUR TEAM", TEAL)
        self.spacer = tk.Frame(body, bg=BG, height=14)
        self.enemies = Roster(body, self.fonts, "ENEMY TEAM", RED)

        footer = tk.Frame(self, bg=PANEL)
        footer.pack(fill="x", side="bottom")
        self.dot = tk.Canvas(
            footer, width=8, height=8, bg=PANEL, highlightthickness=0
        )
        self.dot_id = self.dot.create_oval(0, 0, 7, 7, fill=RED, outline="")
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
        cell.grid(row=0, column=column, sticky="ew")
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
        self.pin.configure(fg=RED if self._pinned else DIM)

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
        self.dot.itemconfigure(self.dot_id, fill=RED if self._pulse else "#4a1c22")
        self.after(700, self._pulse_dot)

    def _apply(self, state: State) -> None:
        if state.kind == source.MATCH and state.info is not None:
            self._show_match(state.info)
            self.status.configure(
                text=f"live · updated {time.strftime('%H:%M:%S')}"
            )
            return

        self._signature = None
        labels = {
            source.STANDBY: ("STANDBY", "Not in a match"),
            source.NO_CLIENT: ("WAITING", "No client"),
            source.ERROR: ("RETRYING", "Reconnecting"),
        }
        badge, headline = labels.get(state.kind, ("WAITING", "Waiting"))
        self.phase.configure(text=badge, fg=GREY)
        self.map_label.configure(text=headline, fg=GREY)
        self.detail.configure(text=state.detail)
        self.server_value.configure(text="—")
        self.side_value.configure(text="—")
        # No point showing empty rosters when there is no match at all.
        self.allies.hide()
        self.enemies.hide()
        self.spacer.pack_forget()
        self.status.configure(text=f"watching · checked {time.strftime('%H:%M:%S')}")

    def _show_match(self, info: MatchInfo) -> None:
        # Only touch the widgets when something actually changed.
        signature = (
            info.match_id,
            info.map_id,
            info.pod_id,
            info.your_team,
            tuple((p.puuid, p.agent_id, p.locked, p.name) for p in info.players),
        )
        if signature == self._signature:
            return
        self._signature = signature

        ally_colour = TEAL if info.your_team == "Blue" else RED
        self.phase.configure(
            text="AGENT SELECT" if info.phase == "pregame" else "IN GAME",
            fg=ally_colour,
        )
        self.map_label.configure(text=map_name(info.map_id), fg=CREAM)
        self.detail.configure(text="")
        self.server_value.configure(text=pod_name(info.pod_id))
        self.side_value.configure(text=info.side, fg=ally_colour)
        self.allies.pack(fill="x")
        self.spacer.pack(fill="x")
        self.enemies.pack(fill="x")
        self.allies.show(
            sorted(info.allies, key=lambda p: not p.is_you), True
        )
        self.enemies.show(info.enemies, False)

    def close(self) -> None:
        self._stop.set()
        self.destroy()


def run(resolve_names: bool = True) -> int:
    app = ValInfoApp(resolve_names=resolve_names)
    app.mainloop()
    return 0
