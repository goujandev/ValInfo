"""Live monitor: sit in the terminal, wait for a match, keep it updated."""

from __future__ import annotations

import sys
import time

from . import render, source
from .render import CREAM, DARK, GREY, RED, Style
from .source import MatchSource, State

ALT_SCREEN_ON = "\033[?1049h"
ALT_SCREEN_OFF = "\033[?1049l"
HOME = "\033[H"
CLEAR_LINE = "\033[K"
CLEAR_BELOW = "\033[J"


def _waiting_rows(style: Style, message: str, detail: str,
                  label: str = "WAITING") -> list[str]:
    right = [
        style("VALORANT", CREAM, bold=True) + "  " + style(label, GREY, bold=True),
        style(render.G["rule"] * 30, DARK),
        style(message, GREY),
        style(detail, GREY, dim=True),
    ]
    return render.side_by_side(render.logo_lines(style), right)


def rows_for(state: State, style: Style) -> list[str]:
    if state.kind == source.MATCH and state.info is not None:
        return render.compose(state.info, style)
    label = {source.STANDBY: "STANDBY", source.ERROR: "RETRYING"}.get(
        state.kind, "WAITING"
    )
    return _waiting_rows(style, state.message, state.detail[:60], label=label)


class Screen:
    """Redraws in place, and only when something actually changed."""

    def __init__(self, style: Style, animate: bool):
        self.style = style
        self.animate = animate
        self.previous: list[str] | None = None

    def draw(self, rows: list[str], footer: str) -> None:
        body = rows + ["", footer]
        if body == self.previous:
            return

        first = self.previous is None
        sys.stdout.write(HOME)
        if first and self.animate:
            render.animate(rows, delay=0.018)
            sys.stdout.write(footer + CLEAR_LINE + "\n")
        else:
            for line in body:
                sys.stdout.write(line + CLEAR_LINE + "\n")
        sys.stdout.write(CLEAR_BELOW)
        sys.stdout.flush()
        self.previous = body

    def tick_footer(self, footer: str) -> None:
        """Repaint just the status line so the spinner keeps moving."""
        if self.previous is None:
            return
        sys.stdout.write(f"\033[{len(self.previous)}H{footer}{CLEAR_LINE}")
        sys.stdout.flush()
        self.previous[-1] = footer


def _footer(style: Style, frame: int, interval: float, note: str) -> str:
    frames = render.G["spin"]
    spin = style(frames[frame % len(frames)], RED)
    label = note or f"live - refreshing every {interval:g}s"
    return f"  {spin} {style(label, GREY, dim=True)}  {style('ctrl+c to quit', DARK)}"


def run(args, style: Style, animate: bool) -> int:
    """Poll until interrupted. Returns a process exit code."""
    screen = Screen(style, animate)
    feed = MatchSource(resolve_names=not args.no_names)
    frame = 0

    if animate:
        sys.stdout.write("\033]0;ValInfo\007")  # window title
        sys.stdout.write(ALT_SCREEN_ON + render.HIDE_CURSOR)
    try:
        while True:
            state = feed.poll()
            if state.restarted:
                screen.previous = None  # force a full repaint
            note = "retrying" if state.kind == source.ERROR else ""
            rows = rows_for(state, style)

            deadline = time.monotonic() + state.interval
            screen.draw(rows, _footer(style, frame, state.interval, note))
            while time.monotonic() < deadline:
                frame += 1
                screen.tick_footer(_footer(style, frame, state.interval, note))
                time.sleep(0.12)
    except KeyboardInterrupt:
        return 0
    finally:
        if animate:
            sys.stdout.write(render.SHOW_CURSOR + ALT_SCREEN_OFF)
        sys.stdout.flush()
