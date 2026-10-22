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

| Source | What you get | Limits |
|---|---|---|
| MLB Stats API | Baseball: career + latest season hitting/pitching | MLB only |
| NHL API | Hockey: current season, career, playoffs | NHL only |
| ESPN | NBA, WNBA, NFL, college sports, some soccer: season + career stat tables | **Unofficial, undocumented API**; ESPN can change or block it at any time. Soccer often has no stat table |
| OpenDota | Dota 2: win rate, rank, top heroes | Search covers **pro players only** |
| Riot Games API | League of Legends: rank, LP, win rate, top champions | **Off unless `RIOT_API_KEY` is set**; needs an exact Riot ID like `Faker#KR1`; dev keys expire every 24h |
| Chess.com | Ratings and W/L/D per time control | Needs the **exact username** |
| Lichess | Ratings per variant, overall record | Fuzzy username search |
| Wikipedia | Anyone with a page (tennis, F1, boxing, cricket, CS/LoL pros, footballers…): career numbers from the infobox, plus club/international apps & goals | Hand-edited, can be out of date; infobox layouts vary so some fields come out messy |
| TheSportsDB | Profiles across most sports | Free tier = **profile only, no stats** |

**Still not covered:** amateur players in most games, Valorant, Fortnite, CS2
match stats, Rocket League, Overwatch, and anyone without a Wikipedia page.
Those need game-specific APIs (often paid or key-based). To add one, write a
new `Provider` subclass in `providers.py` with `search()` and `details()`
(and `enabled()` if it needs a key), then add it to `PROVIDERS`.

### Optional: League of Legends

Get a free development key at https://developer.riotgames.com, then:

```
export RIOT_API_KEY=RGAPI-...
export RIOT_REGION=europe     # americas (default) / europe / asia
export RIOT_PLATFORM=euw1     # na1 (default) / euw1 / kr / ...
python app.py
```

## How it works

- `providers.py`: one class per data source, each turning that API's JSON into
  the same simple shape (name, subtitle, image, sections of `[label, value]` rows).
- `app.py`: `/api/search?q=` runs every provider in parallel threads, so a slow or
  broken API is reported as "unavailable" instead of breaking the search.
  `/api/player/<source>/<id>` loads one player's full stats.
- `static/app.js`: the front end, plain JavaScript, no framework.
