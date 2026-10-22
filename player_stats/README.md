# Player Stats Search

A small Flask website: type a player's name, and it searches several free sports
and esports APIs at once, then shows their stats.

```
cd player_stats
pip install -r requirements.txt
python app.py          # open http://127.0.0.1:5000
python -m unittest discover tests   # offline tests, no internet needed
```

## What it covers (honestly)

On by default (free, no key):

| Source | What you get | Limits |
|---|---|---|
| MLB Stats API | Baseball: career + latest season hitting/pitching | MLB only |
| NHL API | Hockey: current season, career, playoffs | NHL only |
| ESPN | NBA, WNBA, NFL, college sports, some soccer: stat tables | **Unofficial, undocumented API**; ESPN can change or block it at any time. Soccer often has no stat table |
| OpenDota | Dota 2: win rate, rank, top heroes | Search covers **pro players only** |
| OverFast | Overwatch 2: ranks, win rate, KDA, per-role and top-hero stats | Search by BattleTag name; private profiles show rank only |
| Chess.com | Ratings and W/L/D per time control | Needs the **exact username** |
| Lichess | Ratings per variant, overall record | Fuzzy username search |
| Wikipedia | Anyone with a page (tennis, F1, boxing, cricket, esports pros, footballers…): infobox career numbers, club/international apps & goals | Hand-edited, can be out of date; infobox layouts vary |
| TheSportsDB | Profiles across most sports | Free tier = **profile only, no stats** |

Off until you add a free key (each switches itself on when its variable is set):

| Source | Game | Env variable | Get a key | Search with |
|---|---|---|---|---|
| Riot Games API | League of Legends | `RIOT_API_KEY` (+ `RIOT_REGION`, `RIOT_PLATFORM`) | developer.riotgames.com (dev keys expire every 24h) | `Name#TAG` |
| HenrikDev | Valorant | `HENRIK_API_KEY` | api.henrikdev.xyz/dashboard | `Name#TAG` |
| Fortnite-API | Fortnite | `FORTNITE_API_KEY` | dash.fortnite-api.com | exact Epic name |
| FACEIT | Counter-Strike 2 | `FACEIT_API_KEY` | developers.faceit.com | FACEIT nickname |
| Apex Legends Status | Apex Legends (PC) | `APEX_API_KEY` | portal.apexlegendsapi.com | exact Origin/EA name |

```
export FACEIT_API_KEY=...   # etc.
python app.py
```

### What has and hasn't been checked

The code was built in a sandbox with no access to these APIs, and all tests use
fake responses. Field names for **OverFast** were checked against its source code
on GitHub, and **ESPN** against a community reference (which led to fallbacks
for both the flat and split stat layouts). **Fortnite, Valorant, FACEIT, Apex, Riot,
MLB, NHL, OpenDota, Chess.com, Lichess, TheSportsDB and Wikipedia** were written
from knowledge of their docs and have *not* been checked against a live
response. If a source shows as "unavailable" or empty, that's the first place
to look.

**Still not covered:** Rocket League and Call of Duty (no public stats API I know of), amateur players in
most traditional sports, and anyone without a Wikipedia page. To add a source,
write a new `Provider` subclass in `providers.py` with `search()` and
`details()` (and `enabled()` if it needs a key), then add it to `PROVIDERS`.

## Checking the sources against the real APIs

```
python check_sources.py          # every enabled source
python check_sources.py espn ow  # just some
```

It searches each source for a well-known player, opens the result, and prints
`OK`, `WARN` (found, but no stat rows) or `FAIL` with the reason. Run it after
setting up, and whenever a source looks broken.

## How it works

- `providers.py`: one class per data source, each turning that API's JSON into
  the same simple shape (name, subtitle, image, sections of `[label, value]` rows).
- `app.py`: `/api/search?q=` runs every provider in parallel threads, so a slow or
  broken API is reported as "unavailable" instead of breaking the search.
  `/api/player/<source>/<id>` loads one player's full stats.
- `static/app.js`: the front end, plain JavaScript, no framework.
