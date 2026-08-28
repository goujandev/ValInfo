# ValInfo

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

## Is this bannable?

No, and the mechanism above is why.

Vanguard bans tools that touch the game: injected code, memory reads, altered
files, automated input. This does none of that. It is an HTTP client. It asks
the Riot Client - politely, with credentials the client itself hands out - for
information you are already being shown on your own screen.

Specifically:

- It never attaches to, reads, or writes the VALORANT process.
- It sends no input to the game and changes nothing in it.
- Every request goes to `127.0.0.1` (your own machine) or Riot's own servers.
- It only reads. There is no endpoint here that changes any state.
- It cannot reveal anything Riot has not already sent to your client - which is
  why enemy players stay hidden during agent select.

This is the same local API that trackers and overlays have used for years. It is
unofficial and unsupported, so nobody can promise anything on Riot's behalf, but
nothing here resembles what actually gets accounts banned.
