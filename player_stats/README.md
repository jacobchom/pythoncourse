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
| OpenDota | Dota 2: win rate, rank, top heroes | Search covers **pro players only** |
| Chess.com | Ratings and W/L/D per time control | Needs the **exact username** |
| Lichess | Ratings per variant, overall record | Fuzzy username search |
| TheSportsDB | Soccer, NBA, NFL, rugby, F1, etc. | Free tier = **profile only, no stats** |
| Wikipedia | Anyone else (LoL, CS, tennis…) | **Summary only, no stats** |

**Not covered with real stats:** NBA, NFL, soccer, League of Legends, Valorant,
Fortnite, CS2. These need paid or key-based APIs (balldontlie, API-Football,
Riot Games API, etc.). To add one, write a new `Provider` subclass in
`providers.py` with `search()` and `details()`, and add it to `PROVIDERS`.

## How it works

- `providers.py`: one class per data source, each turning that API's JSON into
  the same simple shape (name, subtitle, image, sections of `[label, value]` rows).
- `app.py`: `/api/search?q=` runs every provider in parallel threads, so a slow or
  broken API is reported as "unavailable" instead of breaking the search.
  `/api/player/<source>/<id>` loads one player's full stats.
- `static/app.js`: the front end, plain JavaScript, no framework.
