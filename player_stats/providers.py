"""Data sources for the player stats site.

Each provider knows how to do two things:
  * search(query)  -> list of short results (name, team, picture...)
  * details(id)    -> a full profile with stat tables

Every provider talks to a free, public API that needs no API key.
No single API covers every sport and game, so the site asks all of
them at once and merges what comes back.
"""

import time
import urllib.parse

import requests

TIMEOUT = 8  # seconds per HTTP request
USER_AGENT = "PlayerStatsSearch/1.0 (student project; github.com/jacobchom/pythoncourse)"

_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})

# Very small in-memory cache so repeated searches don't hammer the APIs.
_cache = {}
CACHE_SECONDS = 600


def get_json(url, params=None, cache_seconds=CACHE_SECONDS):
    """GET a URL and return parsed JSON, or None for a 404."""
    key = url + "?" + urllib.parse.urlencode(sorted((params or {}).items()))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < cache_seconds:
        return hit[1]
    response = _session.get(url, params=params, timeout=TIMEOUT)
    if response.status_code == 404:
        data = None
    else:
        response.raise_for_status()
        data = response.json()
    _cache[key] = (time.time(), data)
    return data


def pick(stats, fields):
    """Turn a dict of raw stats into [label, value] rows, skipping missing ones.

    fields is a list of (key, label) pairs.
    """
    rows = []
    for key, label in fields:
        value = stats.get(key)
        if value is None or value == "":
            continue
        if isinstance(value, float):
            value = round(value, 3)
        rows.append([label, value])
    return rows


def section(title, rows):
    return {"title": title, "rows": rows} if rows else None


def profile(name, subtitle="", image=None, sections=(), links=(), note=None):
    return {
        "name": name,
        "subtitle": subtitle,
        "image": image,
        "sections": [s for s in sections if s],
        "links": list(links),
        "note": note,
    }


class Provider:
    key = ""         # short id used in URLs
    label = ""       # name of the data source
    category = ""    # sport / game shown on the result card
    has_stats = True # False for sources that only give a bio

    def search(self, query):
        raise NotImplementedError

    def details(self, player_id):
        raise NotImplementedError

    def result(self, player_id, name, subtitle="", image=None, category=None):
        return {
            "source": self.key,
            "source_label": self.label,
            "category": category or self.category,
            "has_stats": self.has_stats,
            "id": str(player_id),
            "name": name,
            "subtitle": subtitle,
            "image": image,
        }


# --------------------------------------------------------------------------
# Baseball - MLB Stats API (statsapi.mlb.com)
# --------------------------------------------------------------------------
class MLBProvider(Provider):
    key = "mlb"
    label = "MLB Stats API"
    category = "Baseball (MLB)"
    base = "https://statsapi.mlb.com/api/v1"

    HITTING = [
        ("gamesPlayed", "Games"), ("atBats", "At bats"), ("avg", "AVG"),
        ("hits", "Hits"), ("homeRuns", "Home runs"), ("rbi", "RBI"),
        ("runs", "Runs"), ("stolenBases", "Stolen bases"),
        ("obp", "OBP"), ("slg", "SLG"), ("ops", "OPS"),
    ]
    PITCHING = [
        ("gamesPlayed", "Games"), ("gamesStarted", "Starts"), ("wins", "Wins"),
        ("losses", "Losses"), ("era", "ERA"), ("inningsPitched", "Innings"),
        ("strikeOuts", "Strikeouts"), ("whip", "WHIP"), ("saves", "Saves"),
    ]

    @staticmethod
    def headshot(player_id):
        return ("https://img.mlbstatic.com/mlb-photos/image/upload/"
                f"w_213,q_auto:best/v1/people/{player_id}/headshot/67/current")

    def search(self, query):
        data = get_json(f"{self.base}/people/search",
                        {"names": query, "sportIds": 1, "hydrate": "currentTeam"}) or {}
        results = []
        for person in data.get("people", [])[:8]:
            bits = [person.get("primaryPosition", {}).get("abbreviation", ""),
                    person.get("currentTeam", {}).get("name", "")]
            results.append(self.result(person["id"], person.get("fullName", "?"),
                                       " · ".join(b for b in bits if b),
                                       self.headshot(person["id"])))
        return results

    def details(self, player_id):
        hydrate = "currentTeam,stats(group=[hitting,pitching],type=[career,yearByYear])"
        data = get_json(f"{self.base}/people/{player_id}", {"hydrate": hydrate})
        if not data or not data.get("people"):
            return None
        person = data["people"][0]
        sections = []
        for block in person.get("stats", []):
            group = block.get("group", {}).get("displayName", "")
            kind = block.get("type", {}).get("displayName", "")
            splits = block.get("splits", [])
            if not splits:
                continue
            fields = self.HITTING if group == "hitting" else self.PITCHING
            if kind == "career":
                sections.append(section(f"Career {group}", pick(splits[0]["stat"], fields)))
            elif kind == "yearByYear":
                latest = splits[-1]
                team = latest.get("team", {}).get("name", "")
                title = f"{latest.get('season', 'Latest')} {group}" + (f" ({team})" if team else "")
                sections.append(section(title, pick(latest["stat"], fields)))
        # Career first, then latest season.
        sections = sorted(filter(None, sections), key=lambda s: not s["title"].startswith("Career"))
        bats_throws = "/".join(filter(None, [person.get("batSide", {}).get("code"),
                                             person.get("pitchHand", {}).get("code")]))
        bio = [[k, v] for k, v in [
            ("Position", person.get("primaryPosition", {}).get("name")),
            ("Team", person.get("currentTeam", {}).get("name")),
            ("Born", person.get("birthDate")),
            ("Height", person.get("height")),
            ("Weight", person.get("weight")),
            ("Bats / Throws", bats_throws),
            ("MLB debut", person.get("mlbDebutDate")),
        ] if v]
        return profile(person.get("fullName", "?"), self.category,
                       self.headshot(player_id), [section("Bio", bio)] + sections,
                       [["MLB.com", f"https://www.mlb.com/player/{player_id}"]])


# --------------------------------------------------------------------------
# Ice hockey - NHL web API (api-web.nhle.com)
# --------------------------------------------------------------------------
class NHLProvider(Provider):
    key = "nhl"
    label = "NHL API"
    category = "Ice hockey (NHL)"

    SKATER = [
        ("gamesPlayed", "Games"), ("goals", "Goals"), ("assists", "Assists"),
        ("points", "Points"), ("plusMinus", "+/-"), ("pim", "Penalty mins"),
        ("powerPlayGoals", "PP goals"), ("gameWinningGoals", "GW goals"),
        ("shots", "Shots"), ("shootingPctg", "Shooting %"),
    ]
    GOALIE = [
        ("gamesPlayed", "Games"), ("wins", "Wins"), ("losses", "Losses"),
        ("otLosses", "OT losses"), ("goalsAgainstAvg", "GAA"),
        ("savePctg", "Save %"), ("shutouts", "Shutouts"),
    ]

    def search(self, query):
        data = get_json("https://search.d3.nhle.com/api/v1/search/player",
                        {"culture": "en-us", "limit": 8, "q": query}) or []
        results = []
        for p in data:
            pid = p.get("playerId")
            if not pid:
                continue
            team = p.get("teamAbbrev") or p.get("lastTeamAbbrev") or ""
            status = "" if p.get("active") else "retired"
            bits = [p.get("positionCode", ""), team, status]
            results.append(self.result(pid, p.get("name", "?"),
                                       " · ".join(b for b in bits if b),
                                       f"https://assets.nhle.com/mugs/nhl/latest/{pid}.png"))
        return results

    def details(self, player_id):
        data = get_json(f"https://api-web.nhle.com/v1/player/{player_id}/landing")
        if not data:
            return None
        name = " ".join(filter(None, [data.get("firstName", {}).get("default"),
                                      data.get("lastName", {}).get("default")]))
        fields = self.GOALIE if data.get("position") == "G" else self.SKATER
        sections = []
        career = data.get("careerTotals", {})
        sections.append(section("Career regular season", pick(career.get("regularSeason", {}), fields)))
        sections.append(section("Career playoffs", pick(career.get("playoffs", {}), fields)))
        current = data.get("featuredStats", {})
        if current.get("regularSeason", {}).get("subSeason"):
            season = str(current.get("season", ""))
            label = f"{season[:4]}-{season[4:]}" if len(season) == 8 else "Current"
            sections.insert(0, section(f"{label} season", pick(current["regularSeason"]["subSeason"], fields)))
        bio = [[k, v] for k, v in [
            ("Position", data.get("position")),
            ("Team", data.get("fullTeamName", {}).get("default")),
            ("Number", data.get("sweaterNumber")),
            ("Born", data.get("birthDate")),
            ("Height (cm)", data.get("heightInCentimeters")),
            ("Weight (kg)", data.get("weightInKilograms")),
        ] if v]
        return profile(name or "?", self.category, data.get("headshot"),
                       [section("Bio", bio)] + sections,
                       [["NHL.com", f"https://www.nhl.com/player/{player_id}"]])


# --------------------------------------------------------------------------
# Dota 2 - OpenDota (api.opendota.com)
# --------------------------------------------------------------------------
class OpenDotaProvider(Provider):
    key = "dota"
    label = "OpenDota"
    category = "Dota 2 (esports)"
    base = "https://api.opendota.com/api"
    MEDALS = ["", "Herald", "Guardian", "Crusader", "Archon", "Legend",
              "Ancient", "Divine", "Immortal"]

    def search(self, query):
        q = query.lower()
        results = []
        # Pro players first: the full list is one request, cached for 6 hours.
        pros = get_json(f"{self.base}/proPlayers", cache_seconds=6 * 3600) or []
        for p in pros:
            name = p.get("name") or ""
            if q in name.lower():
                sub = " · ".join(filter(None, ["Pro", p.get("team_name"), p.get("country_code", "").upper()]))
                results.append(self.result(p["account_id"], name, sub, p.get("avatarfull")))
                if len(results) >= 6:
                    break
        return results

    def rank(self, tier):
        if not tier:
            return None
        medal, stars = divmod(int(tier), 10)
        name = self.MEDALS[medal] if medal < len(self.MEDALS) else str(tier)
        return f"{name} {stars}" if stars and medal < 8 else name

    def details(self, player_id):
        player = get_json(f"{self.base}/players/{player_id}")
        if not player or not player.get("profile"):
            return None
        prof = player["profile"]
        wl = get_json(f"{self.base}/players/{player_id}/wl") or {}
        win, lose = wl.get("win", 0), wl.get("lose", 0)
        overview = [[k, v] for k, v in [
            ("Matches", win + lose),
            ("Wins", win),
            ("Losses", lose),
            ("Win rate", f"{win / (win + lose):.1%}" if win + lose else None),
            ("Rank", self.rank(player.get("rank_tier"))),
            ("Leaderboard", player.get("leaderboard_rank")),
        ] if v not in (None, "")]

        heroes_rows = []
        heroes = get_json(f"{self.base}/players/{player_id}/heroes") or []
        names = {h["id"]: h["localized_name"]
                 for h in (get_json(f"{self.base}/heroes", cache_seconds=86400) or [])}
        for h in heroes[:5]:
            games = h.get("games", 0)
            if not games:
                continue
            rate = h.get("win", 0) / games
            heroes_rows.append([names.get(h.get("hero_id"), f"Hero {h.get('hero_id')}"),
                                f"{games} games · {rate:.0%} wins"])

        display = prof.get("name") or prof.get("personaname") or "?"
        sub = self.category if not prof.get("name") else f"{self.category} · Steam: {prof.get('personaname')}"
        note = None
        if not win + lose:
            note = "This player's match history is private or not tracked by OpenDota."
        return profile(display, sub, prof.get("avatarfull"),
                       [section("Overview", overview), section("Most played heroes", heroes_rows)],
                       [["OpenDota", f"https://www.opendota.com/players/{player_id}"]], note)


# --------------------------------------------------------------------------
# Chess - Chess.com public API (exact usernames only)
# --------------------------------------------------------------------------
class ChessComProvider(Provider):
    key = "chesscom"
    label = "Chess.com"
    category = "Chess (Chess.com)"
    base = "https://api.chess.com/pub/player"
    MODES = [("chess_rapid", "Rapid"), ("chess_blitz", "Blitz"),
             ("chess_bullet", "Bullet"), ("chess_daily", "Daily")]

    def search(self, query):
        username = query.replace(" ", "").lower()
        if not username.isascii() or not username.replace("-", "").replace("_", "").isalnum():
            return []
        data = get_json(f"{self.base}/{username}")
        if not data or "username" not in data:
            return []
        sub = " · ".join(filter(None, [data.get("title"), "@" + data["username"]]))
        return [self.result(data["username"], data.get("name") or data["username"], sub, data.get("avatar"))]

    def details(self, player_id):
        prof = get_json(f"{self.base}/{player_id}")
        if not prof:
            return None
        stats = get_json(f"{self.base}/{player_id}/stats") or {}
        sections = []
        for key, label in self.MODES:
            mode = stats.get(key)
            if not mode:
                continue
            record = mode.get("record", {})
            sections.append(section(label, [[k, v] for k, v in [
                ("Current rating", mode.get("last", {}).get("rating")),
                ("Best rating", mode.get("best", {}).get("rating")),
                ("Wins", record.get("win")),
                ("Losses", record.get("loss")),
                ("Draws", record.get("draw")),
            ] if v is not None]))
        if stats.get("tactics", {}).get("highest"):
            sections.append(section("Puzzles", [["Highest rating", stats["tactics"]["highest"].get("rating")]]))
        sub = " · ".join(filter(None, [prof.get("title"), "@" + prof.get("username", player_id), self.category]))
        return profile(prof.get("name") or prof.get("username", player_id), sub, prof.get("avatar"),
                       sections, [["Chess.com", prof.get("url", f"https://www.chess.com/member/{player_id}")]])


# --------------------------------------------------------------------------
# Chess - Lichess (has a real fuzzy search)
# --------------------------------------------------------------------------
class LichessProvider(Provider):
    key = "lichess"
    label = "Lichess"
    category = "Chess (Lichess)"
    MODES = [("bullet", "Bullet"), ("blitz", "Blitz"), ("rapid", "Rapid"),
             ("classical", "Classical"), ("correspondence", "Correspondence"),
             ("puzzle", "Puzzles")]

    def search(self, query):
        term = query.replace(" ", "")
        if len(term) < 3:
            return []
        data = get_json("https://lichess.org/api/player/autocomplete",
                        {"term": term, "object": "true"}) or {}
        results = []
        for u in data.get("result", [])[:5]:
            sub = " · ".join(filter(None, [u.get("title"), "@" + u.get("name", "")]))
            results.append(self.result(u.get("id"), u.get("name", "?"), sub))
        return results

    def details(self, player_id):
        user = get_json(f"https://lichess.org/api/user/{player_id}")
        if not user or user.get("disabled"):
            return None
        perfs = user.get("perfs", {})
        ratings = []
        for key, label in self.MODES:
            p = perfs.get(key)
            if p and p.get("games"):
                ratings.append([label, f"{p.get('rating')} ({p.get('games')} games)"])
        count = user.get("count", {})
        record = pick(count, [("all", "Games"), ("win", "Wins"), ("loss", "Losses"), ("draw", "Draws")])
        name = user.get("username", player_id)
        sub = " · ".join(filter(None, [user.get("title"), self.category]))
        return profile(name, sub, None,
                       [section("Ratings", ratings), section("Record", record)],
                       [["Lichess", user.get("url", f"https://lichess.org/@/{player_id}")]])


# --------------------------------------------------------------------------
# Every other sport - TheSportsDB (free tier: profiles, not detailed stats)
# --------------------------------------------------------------------------
class SportsDBProvider(Provider):
    key = "sportsdb"
    label = "TheSportsDB"
    category = "Multi-sport"
    has_stats = False
    base = "https://www.thesportsdb.com/api/v1/json/3"  # "3" is the public free key

    def search(self, query):
        data = get_json(f"{self.base}/searchplayers.php", {"p": query}) or {}
        results = []
        for p in (data.get("player") or [])[:8]:
            bits = [p.get("strPosition"), p.get("strTeam"), p.get("strNationality")]
            results.append(self.result(p["idPlayer"], p.get("strPlayer", "?"),
                                       " · ".join(b for b in bits if b and b != "_Retired Soccer"),
                                       p.get("strCutout") or p.get("strThumb"),
                                       p.get("strSport") or self.category))
        return results

    def details(self, player_id):
        data = get_json(f"{self.base}/lookupplayer.php", {"id": player_id}) or {}
        players = data.get("players") or data.get("player") or []
        if not players:
            return None
        p = players[0]
        bio = [[k, v] for k, v in [
            ("Sport", p.get("strSport")),
            ("Team", p.get("strTeam")),
            ("Position", p.get("strPosition")),
            ("Number", p.get("strNumber")),
            ("Nationality", p.get("strNationality")),
            ("Born", p.get("dateBorn")),
            ("Birthplace", p.get("strBirthLocation")),
            ("Height", p.get("strHeight")),
            ("Weight", p.get("strWeight")),
            ("Status", p.get("strStatus")),
        ] if v]
        about = (p.get("strDescriptionEN") or "").strip()
        sections = [section("Profile", bio)]
        if about:
            sections.append({"title": "About", "text": about[:1500] + ("…" if len(about) > 1500 else "")})
        return profile(p.get("strPlayer", "?"), p.get("strSport", self.category),
                       p.get("strCutout") or p.get("strThumb"), sections,
                       [["TheSportsDB", f"https://www.thesportsdb.com/player/{player_id}"]],
                       "TheSportsDB's free tier gives profiles, not match-by-match stats.")


# --------------------------------------------------------------------------
# Fallback for anyone else (LoL, CS, tennis, F1...) - Wikipedia
# --------------------------------------------------------------------------
class WikipediaProvider(Provider):
    key = "wiki"
    label = "Wikipedia"
    category = "Wikipedia"
    has_stats = False
    SPORTY = ("player", "athlete", "footballer", "cricketer", "gamer", "esports",
              "racing", "driver", "boxer", "fighter", "tennis", "golfer", "swimmer",
              "runner", "sprinter", "skater", "wrestler", "cyclist", "olympi",
              "basketball", "baseball", "hockey", "quarterback", "chess", "coach")

    def search(self, query):
        data = get_json("https://en.wikipedia.org/w/api.php", {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": query, "gsrlimit": 8, "prop": "description|pageimages",
            "piprop": "thumbnail", "pithumbsize": 200,
        }) or {}
        pages = sorted(data.get("query", {}).get("pages", {}).values(),
                       key=lambda p: p.get("index", 99))
        results = []
        for page in pages:
            desc = page.get("description", "")
            # Only keep pages that look like they are about a competitor.
            if not any(word in desc.lower() for word in self.SPORTY):
                continue
            results.append(self.result(page["title"], page["title"], desc,
                                       page.get("thumbnail", {}).get("source")))
            if len(results) >= 3:
                break
        return results

    def details(self, player_id):
        title = urllib.parse.quote(player_id.replace(" ", "_"), safe="")
        data = get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
        if not data:
            return None
        return profile(data.get("title", player_id), data.get("description", ""),
                       data.get("thumbnail", {}).get("source"),
                       [{"title": "Summary", "text": data.get("extract", "")}],
                       [["Wikipedia", data.get("content_urls", {}).get("desktop", {}).get(
                           "page", f"https://en.wikipedia.org/wiki/{title}")]],
                       "Wikipedia gives a summary, not a stats table. Check the full article for career stats.")


PROVIDERS = [MLBProvider(), NHLProvider(), OpenDotaProvider(), ChessComProvider(),
             LichessProvider(), SportsDBProvider(), WikipediaProvider()]
BY_KEY = {p.key: p for p in PROVIDERS}
