# ValInfo

Read-only VALORANT match info from Riot's **local** client API. No third-party
services, no injection, no automation — it reads the lockfile, asks the running
client for its tokens, and queries Riot's own glz/pd endpoints.

## Download

Grab **`ValInfo.exe`** from the [Releases](../../releases/latest) page. One file,
nothing to install. Double-click it and you are done.

Windows will warn that the app is unsigned the first time - "More info" then
"Run anyway". Code signing certificates cost money; the source is all here
instead, and every release is built by GitHub Actions from this repository, so
the exe you download matches the code you can read above.

## Requirements

Running the exe needs nothing at all. To run from source:

- Windows (the game client only runs there)
- Python 3.11+
- `pip install -r requirements.txt`

## Running it

Double-click **`dist\ValInfo.exe`**. A window opens, waits for VALORANT, and
fills itself in the moment agent select starts - map, server, side, and every
player's agent, refreshing on its own until you close it. **PIN** in the top
right keeps it above other windows.

No Python, no install, no terminal on the machine that runs it. If you have the
source checked out instead, `ValInfo.bat` opens the same window.

### Terminal version

The neofetch-style console UI is still there:

```bash
python -m valinfo live
```

Or `ValInfo-terminal.bat`. Other commands:

- `valinfo` (or `valinfo gui`) - the desktop window, the default
- `valinfo live` - watch continuously in the terminal
- `valinfo once` - print the current match and exit
- `valinfo auth` - show local auth details, to check the connection

Flags: `--json` (on `once`) for machine-readable output, `--no-names` to skip
Riot ID lookups, `--no-color` / `--no-anim` to strip the terminal styling.

## Building the executable

```bash
build.bat
```

That installs PyInstaller, regenerates the icon, and produces a standalone
`dist\ValInfo.exe`. Windows SmartScreen warns on first run because the binary
is unsigned - "More info" then "Run anyway" once, and it stops asking.

## How it works

1. Reads `%LocalAppData%\Riot Games\Riot Client\Config\lockfile`
   (`name:pid:port:password:protocol`) for the local port and password.
2. `GET https://127.0.0.1:{port}/entitlements/v1/token` with Basic auth
   (`riot:{password}`) → access token, entitlements token, PUUID.
3. Region/shard and client version come from `ShooterGame.log`, with the Riot
   Client's `/riotclient/region-locale` as a fallback for the region.
4. Match state:
   - core-game: `/core-game/v1/players/{puuid}` → `/core-game/v1/matches/{id}`
   - pregame: `/pregame/v1/players/{puuid}` → `/pregame/v1/matches/{id}`
5. Agent, map, mode, and game-pod IDs are resolved through the bundled tables in
   `valinfo/content.py`.

Requests to the regional APIs carry `Authorization: Bearer`,
`X-Riot-Entitlements-JWT`, `X-Riot-ClientPlatform`, and `X-Riot-ClientVersion`.

## Notes

- TLS verification is disabled for `127.0.0.1` only because the Riot Client uses
  a self-signed certificate.
- Enemy players are not exposed by the API during agent select; they appear once
  the match starts.
- Players who hide their Riot ID come back from the name service with an empty
  name; they are shown as "hidden".
- `VALINFO_CLIENT_VERSION` overrides the version parsed from the log, in case a
  patch changes the log format.
- Agent/map tables need an entry when Riot ships new content; unknown IDs are
  printed rather than dropped.
- `Side` is the first-half side. It does not flip at halftime, because the API
  does not report the round number.
