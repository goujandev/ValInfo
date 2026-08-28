"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from dataclasses import asdict

from . import live, render
from .client import ClientError, ValorantClient
from .content import agent_name, map_name, mode_name, pod_name
from .lockfile import LockfileError, read_lockfile
from .match import MatchInfo, current_match
from .render import CREAM, GREY, RED, Style


def match_json(info: MatchInfo) -> str:
    data = asdict(info)
    data["side"] = info.side
    data["map"] = map_name(info.map_id)
    data["mode"] = mode_name(info.mode_id)
    data["server"] = pod_name(info.pod_id)
    for player, raw in zip(info.players, data["players"]):
        raw["agent"] = agent_name(player.agent_id)
    return json.dumps(data, indent=2)


def print_auth(client: ValorantClient, style: Style) -> None:
    auth = client.auth
    rows = [
        style("LOCAL AUTH", CREAM, bold=True),
        style(render.G["rule"] * 30, render.DARK),
    ]
    fields = [
        ("PORT", str(client.lockfile.port)),
        ("PUUID", auth.puuid),
        ("REGION", f"{client.region} / {client.shard}"),
        ("VERSION", client.client_version),
        ("TOKEN", f"{auth.access_token[:28]}  ({len(auth.access_token)} chars)"),
        ("ENTITLEMENT",
         f"{auth.entitlements_token[:28]}  ({len(auth.entitlements_token)} chars)"),
    ]
    rows += [style(f"{k:<12}", GREY) + style(v, CREAM) for k, v in fields]
    print("\n".join(render.side_by_side(render.logo_lines(style), rows)))


def _fetch(client: ValorantClient, args, style: Style, spin: bool) -> MatchInfo | None:
    """Query the client, spinning while we wait."""
    result: list = []

    def work():
        try:
            result.append(current_match(client, resolve_names=not args.no_names))
        except Exception as exc:  # surfaced on the main thread
            result.append(exc)

    thread = threading.Thread(target=work, daemon=True)
    with render.Spinner("reading match state", style, enabled=spin) as spinner:
        thread.start()
        while thread.is_alive():
            spinner.tick()
            time.sleep(0.08)
        thread.join()

    value = result[0] if result else None
    if isinstance(value, Exception):
        raise value
    return value


def _once(client: ValorantClient, args, style: Style, animate: bool) -> None:
    info = _fetch(client, args, style, spin=animate)

    if args.json:
        print(json.dumps({"in_match": False}) if info is None else match_json(info))
        return

    rows = render.idle(style) if info is None else render.compose(info, style)
    render.animate(rows, delay=0.018 if animate else 0.0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="valinfo",
        description="Read-only VALORANT match info from the local Riot client API.",
    )
    sub = parser.add_subparsers(dest="command")

    p_gui = sub.add_parser("gui", help="open the desktop window (default)")
    p_live = sub.add_parser("live", help="watch continuously in the terminal")
    p_once = sub.add_parser("once", help="print the current match and exit")
    p_once.add_argument("--json", action="store_true", help="machine-readable output")
    p_auth = sub.add_parser("auth", help="print local auth details")

    for p in (p_gui, p_live, p_once, p_auth):
        p.add_argument("--no-color", action="store_true", help="disable colour")
        p.add_argument("--no-anim", action="store_true", help="disable animation")
        p.add_argument(
            "--no-names", action="store_true", help="skip Riot ID lookups"
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    # "gui" is the default subcommand: valinfo == valinfo gui
    if not argv or argv[0] not in {"gui", "live", "once", "auth", "-h", "--help"}:
        argv.insert(0, "gui")
    args = parser.parse_args(argv)

    if args.command == "gui":
        from . import gui  # imported lazily so the CLI works without tkinter

        return gui.run(resolve_names=not args.no_names)

    render.setup_stdout()
    # A windowed build has no console at all, so stdout can be None.
    tty = bool(sys.stdout) and sys.stdout.isatty()
    color = not args.no_color and not os.environ.get("NO_COLOR") and tty
    if color:
        color = render.enable_ansi()
    style = Style(color)
    animate = tty and not args.no_anim and not getattr(args, "json", False)

    try:
        if args.command == "live":
            return live.run(args, style, animate)

        client = ValorantClient(read_lockfile())
        if args.command == "auth":
            print_auth(client, style)
            return 0
        _once(client, args, style, animate)
    except KeyboardInterrupt:
        sys.stdout.write(render.SHOW_CURSOR + "\n")
        return 130
    except (LockfileError, ClientError) as exc:
        print(f"{style('error:', RED, bold=True)} {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
