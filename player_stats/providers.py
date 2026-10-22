"""Data sources for the player stats site.

Each provider knows how to do two things:
  * search(query)  -> list of short results (name, team, picture...)
  * details(id)    -> a full profile with stat tables

Every provider talks to a free, public API that needs no API key.
No single API covers every sport and game, so the site asks all of
them at once and merges what comes back.
"""

import os
import re
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


def get_json(url, params=None, cache_seconds=CACHE_SECONDS, headers=None):
    """GET a URL and return parsed JSON, or None for a 404."""
    key = url + "?" + urllib.parse.urlencode(sorted((params or {}).items()))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < cache_seconds:
        return hit[1]
    response = _session.get(url, params=params, timeout=TIMEOUT, headers=headers)
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

    def enabled(self):
        """Providers that need an API key switch themselves off without one."""
        return True

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
# NBA, NFL, soccer, college, WNBA... - ESPN's public site API
# (unofficial: ESPN doesn't document it and could change it at any time)
# --------------------------------------------------------------------------
class ESPNProvider(Provider):
    key = "espn"
    label = "ESPN"
    category = "Sports (ESPN)"
    base = "https://site.web.api.espn.com/apis/common/v3"

    # ESPN ids found inside "uid" strings like "s:40~l:46~a:1966".
    SPORTS = {"40": "basketball", "20": "football", "1": "baseball", "70": "hockey",
              "600": "soccer", "850": "tennis", "1100": "golf", "2000": "racing", "3301": "mma"}
    LEAGUES = {"46": "nba", "59": "wnba", "41": "mens-college-basketball",
               "54": "womens-college-basketball", "28": "nfl", "23": "college-football",
               "10": "mlb", "90": "nhl"}
    NICE = {"nba": "Basketball (NBA)", "wnba": "Basketball (WNBA)", "nfl": "American football (NFL)",
            "college-football": "College football", "mens-college-basketball": "College basketball",
            "womens-college-basketball": "College basketball"}
    SKIP = {"mlb", "nhl"}  # the official MLB and NHL APIs are better

    @staticmethod
    def slug(value):
        if isinstance(value, dict):
            return value.get("slug") or value.get("abbreviation", "").lower() or None
        return value or None

    def where(self, item):
        sport, league = self.slug(item.get("sport")), self.slug(item.get("league"))
        uid = dict(part.split(":", 1) for part in (item.get("uid") or "").split("~") if ":" in part)
        sport = sport or self.SPORTS.get(uid.get("s"))
        league = league or self.LEAGUES.get(uid.get("l"))
        return sport, league, item.get("id") or uid.get("a")

    def search(self, query):
        data = get_json(f"{self.base}/search", {"query": query, "limit": 10, "type": "player"}) or {}
        results = []
        for item in data.get("items", []):
            if item.get("type", "player") != "player":
                continue
            sport, league, aid = self.where(item)
            if not (sport and league and aid) or league in self.SKIP:
                continue
            image = (item.get("headshot") or {}).get("href") if isinstance(item.get("headshot"), dict) else None
            category = self.NICE.get(league, f"{sport.title()} ({league.upper()})")
            results.append(self.result(f"{sport}/{league}/{aid}", item.get("displayName", "?"),
                                       item.get("description") or item.get("subtitle") or "",
                                       image, category))
            if len(results) >= 6:
                break
        return results or self.search_v2(query)

    def search_v2(self, query):
        """Fallback: ESPN's general site search, which groups hits by type."""
        data = get_json("https://site.web.api.espn.com/apis/search/v2", {"query": query, "limit": 10}) or {}
        results = []
        for group in data.get("results", []):
            if group.get("type") != "player":
                continue
            for item in group.get("contents", []):
                sport, league, aid = self.where({**item, "league": item.get("defaultLeagueSlug") or item.get("league")})
                if not (sport and league and aid) or league in self.SKIP:
                    continue
                image = item.get("image", {}).get("default") if isinstance(item.get("image"), dict) else None
                results.append(self.result(f"{sport}/{league}/{aid}", item.get("displayName", "?"),
                                           item.get("subtitle") or item.get("description") or "", image,
                                           self.NICE.get(league, f"{sport.title()} ({league.upper()})")))
        return results[:6]

    def athlete(self, sport, league, aid):
        """Bio from the common v3 endpoint, falling back to the documented Core API."""
        for url in (f"{self.base}/sports/{sport}/{league}/athletes/{aid}",
                    f"https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/athletes/{aid}"):
            try:
                data = get_json(url) or {}
            except requests.RequestException:
                continue
            athlete = data.get("athlete", data)
            if athlete.get("displayName"):
                return athlete
        return None

    @staticmethod
    def stat_sections(stats):
        """ESPN returns either several splits (season, career) or one flat list."""
        labels = stats.get("displayNames") or stats.get("labels") or []
        sections = []
        for split in stats.get("splits", []):
            values = split.get("stats", [])
            rows = [[label, value] for label, value in zip(labels, values) if value not in (None, "")]
            sections.append(section(split.get("displayName", "Stats"), rows))
        values = stats.get("displayValues") or stats.get("values")
        if not sections and values:
            rows = [[label, value] for label, value in zip(labels, values) if value not in (None, "")]
            sections.append(section(stats.get("displayName") or "Current season", rows))
        return sections

    def details(self, player_id):
        try:
            sport, league, aid = player_id.split("/")
        except ValueError:
            return None
        athlete = self.athlete(sport, league, aid)
        if not athlete:
            return None
        overview = get_json(f"{self.base}/sports/{sport}/{league}/athletes/{aid}/overview") or {}

        sections = []
        bio = [[k, v] for k, v in [
            ("Team", (athlete.get("team") or {}).get("displayName")),  # Core API gives a $ref here
            ("Position", (athlete.get("position") or {}).get("displayName")),
            ("Number", athlete.get("jersey")),
            ("Born", athlete.get("displayDOB")),
            ("Height", athlete.get("displayHeight")),
            ("Weight", athlete.get("displayWeight")),
            ("Experience", (athlete.get("displayExperience"))),
        ] if v]
        sections.append(section("Bio", bio))

        sections += self.stat_sections(overview.get("statistics") or {})

        note = None
        if len(sections) == 1 or not any(s for s in sections[1:]):
            note = "ESPN had no stat table for this player (common for soccer and retired players)."
        headshot = athlete.get("headshot")
        return profile(athlete["displayName"], self.NICE.get(league, f"{sport.title()} ({league.upper()})"),
                       headshot.get("href") if isinstance(headshot, dict) else None, sections,
                       [["ESPN", f"https://www.espn.com/{sport}/player/_/id/{aid}"]], note)


# --------------------------------------------------------------------------
# League of Legends - Riot Games API (needs a free key: set RIOT_API_KEY)
# --------------------------------------------------------------------------
class RiotProvider(Provider):
    key = "lol"
    label = "Riot Games API"
    category = "League of Legends"

    def enabled(self):
        return bool(os.environ.get("RIOT_API_KEY"))

    @property
    def headers(self):
        return {"X-Riot-Token": os.environ.get("RIOT_API_KEY", "")}

    @property
    def region(self):    # account lookups: americas / europe / asia
        return os.environ.get("RIOT_REGION", "americas")

    @property
    def platform(self):  # game servers: na1, euw1, kr...
        return os.environ.get("RIOT_PLATFORM", "na1")

    def ddragon(self):
        versions = get_json("https://ddragon.leagueoflegends.com/api/versions.json", cache_seconds=86400)
        return versions[0] if versions else None

    def search(self, query):
        # Riot only lets you look up exact Riot IDs, written as Name#TAG.
        if "#" not in query:
            return []
        name, tag = (part.strip() for part in query.split("#", 1))
        if not name or not tag:
            return []
        url = (f"https://{self.region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
               f"{urllib.parse.quote(name)}/{urllib.parse.quote(tag)}")
        account = get_json(url, headers=self.headers)
        if not account:
            return []
        return [self.result(account["puuid"], f"{account.get('gameName')}#{account.get('tagLine')}",
                            f"Server: {self.platform.upper()}")]

    def details(self, puuid):
        platform = f"https://{self.platform}.api.riotgames.com"
        account = get_json(f"https://{self.region}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}",
                           headers=self.headers)
        if not account:
            return None
        summoner = get_json(f"{platform}/lol/summoner/v4/summoners/by-puuid/{puuid}", headers=self.headers) or {}
        leagues = get_json(f"{platform}/lol/league/v4/entries/by-puuid/{puuid}", headers=self.headers) or []
        mastery = get_json(f"{platform}/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/top",
                           {"count": 5}, headers=self.headers) or []

        version = self.ddragon()
        champs = {}
        if version:
            data = get_json(f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json",
                            cache_seconds=86400) or {}
            champs = {int(c["key"]): c["name"] for c in data.get("data", {}).values()}

        sections = [section("Account", [[k, v] for k, v in [
            ("Summoner level", summoner.get("summonerLevel")), ("Server", self.platform.upper())] if v])]
        queues = {"RANKED_SOLO_5x5": "Ranked Solo/Duo", "RANKED_FLEX_SR": "Ranked Flex"}
        for entry in leagues:
            wins, losses = entry.get("wins", 0), entry.get("losses", 0)
            sections.append(section(queues.get(entry.get("queueType"), entry.get("queueType", "Ranked")), [
                ["Rank", f"{entry.get('tier', '').title()} {entry.get('rank', '')}".strip()],
                ["LP", entry.get("leaguePoints")],
                ["Wins", wins], ["Losses", losses],
                ["Win rate", f"{wins / (wins + losses):.1%}" if wins + losses else "-"],
            ]))
        sections.append(section("Top champions (mastery)", [
            [champs.get(m.get("championId"), f"Champion {m.get('championId')}"),
             f"Level {m.get('championLevel')} · {m.get('championPoints', 0):,} pts"] for m in mastery]))
        icon = summoner.get("profileIconId")
        image = (f"https://ddragon.leagueoflegends.com/cdn/{version}/img/profileicon/{icon}.png"
                 if version and icon is not None else None)
        name = f"{account.get('gameName')}#{account.get('tagLine')}"
        return profile(name, self.category, image, sections,
                       [["op.gg", f"https://www.op.gg/summoners/{self.platform[:-1] if self.platform[-1].isdigit() else self.platform}/"
                                  f"{urllib.parse.quote(account.get('gameName', ''))}-{urllib.parse.quote(account.get('tagLine', ''))}"]],
                       None if leagues else "Unranked this season.")


# --------------------------------------------------------------------------
# Overwatch 2 - OverFast API (free, no key; reads public Blizzard profiles)
# Field names checked against app/api/models/players.py in TeKrop/overfast-api.
# --------------------------------------------------------------------------
class OverwatchProvider(Provider):
    key = "ow"
    label = "OverFast (Overwatch)"
    category = "Overwatch 2"
    base = "https://overfast-api.tekrop.fr"

    def search(self, query):
        name = query.split("#")[0].strip()
        if len(name) < 3 or " " in name:
            return []  # BattleTags never contain spaces
        data = get_json(f"{self.base}/players", {"name": name, "limit": 6}) or {}
        results = []
        for p in data.get("results", []):
            sub = "Public profile" if p.get("is_public", True) else "Private profile"
            results.append(self.result(p["player_id"], p.get("name", p["player_id"]), sub, p.get("avatar")))
        return results

    @staticmethod
    def summary_rows(stats):
        avg = stats.get("average") or {}
        rows = [[k, v] for k, v in [
            ("Games", stats.get("games_played")),
            ("Wins", stats.get("games_won")),
            ("Win rate", f"{stats['winrate']}%" if stats.get("winrate") is not None else None),
            ("KDA", stats.get("kda")),
            ("Hours played", round(stats["time_played"] / 3600, 1) if stats.get("time_played") else None),
            ("Elims / 10 min", avg.get("eliminations")),
            ("Damage / 10 min", avg.get("damage")),
            ("Healing / 10 min", avg.get("healing")),
        ] if v is not None]
        return rows

    def details(self, player_id):
        summary = get_json(f"{self.base}/players/{player_id}/summary")
        if not summary:
            return None
        sections = []
        ranks = []
        for platform, ladder in (summary.get("competitive") or {}).items():
            for role in ("tank", "damage", "support", "open"):
                rank = (ladder or {}).get(role)
                if rank and rank.get("division"):
                    ranks.append([f"{role.title()} ({platform.upper()})",
                                  f"{rank['division'].title()} {rank.get('tier', '')}".strip()])
        sections.append(section("Competitive rank", ranks))
        endorsement = (summary.get("endorsement") or {}).get("level")
        if endorsement:
            sections.append(section("Profile", [["Endorsement level", endorsement]]))

        stats = get_json(f"{self.base}/players/{player_id}/stats/summary") or {}
        sections.append(section("All heroes", self.summary_rows(stats.get("general") or {})))
        for role, role_stats in (stats.get("roles") or {}).items():
            if role_stats:
                sections.append(section(role.title(), self.summary_rows(role_stats)))
        heroes = sorted((stats.get("heroes") or {}).items(),
                        key=lambda kv: -(kv[1] or {}).get("time_played", 0))
        top = [[hero.replace("-", " ").title(),
                f"{(h or {}).get('games_played', 0)} games · {(h or {}).get('winrate', 0)}% wins"]
               for hero, h in heroes[:5] if h]
        sections.append(section("Most played heroes", top))
        note = None if stats.get("general") else "This profile is private, so only the rank is visible."
        return profile(summary.get("username", player_id), self.category, summary.get("avatar"), sections,
                       [["Overwatch career", f"https://overwatch.blizzard.com/en-us/career/{player_id}/"]], note)


# --------------------------------------------------------------------------
# Fortnite - fortnite-api.com (free key: set FORTNITE_API_KEY)
# Field names written from memory of the API docs; not verified offline.
# --------------------------------------------------------------------------
class FortniteProvider(Provider):
    key = "fortnite"
    label = "Fortnite-API"
    category = "Fortnite"

    def enabled(self):
        return bool(os.environ.get("FORTNITE_API_KEY"))

    def stats(self, name):
        return get_json("https://fortnite-api.com/v2/stats/br/v2", {"name": name},
                        headers={"Authorization": os.environ.get("FORTNITE_API_KEY", "")})

    def search(self, query):
        # Exact Epic display name only. 403 = private stats, 404 = no such player.
        try:
            data = self.stats(query.strip())
        except requests.HTTPError:
            return []
        account = ((data or {}).get("data") or {}).get("account")
        if not account:
            return []
        return [self.result(account["name"], account["name"], "Epic account")]

    def details(self, player_id):
        data = (self.stats(player_id) or {}).get("data")
        if not data:
            return None
        sections = []
        bp = data.get("battlePass") or {}
        if bp.get("level") is not None:
            sections.append(section("Battle pass", [["Level", bp["level"]], ["Progress", f"{bp.get('progress', 0)}%"]]))
        modes = (data.get("stats") or {}).get("all") or {}
        for mode, title in (("overall", "Overall"), ("solo", "Solo"), ("duo", "Duos"), ("squad", "Squads")):
            m = modes.get(mode)
            if m:
                sections.append(section(title, pick(m, [
                    ("matches", "Matches"), ("wins", "Wins"), ("winRate", "Win %"), ("kills", "Kills"),
                    ("kd", "K/D"), ("killsPerMatch", "Kills / match"), ("top10", "Top 10"),
                    ("minutesPlayed", "Minutes played")])))
        return profile(data["account"]["name"], self.category, None, sections,
                       [["Fortnite Tracker", f"https://fortnitetracker.com/profile/all/{urllib.parse.quote(player_id)}"]])


# --------------------------------------------------------------------------
# Valorant - HenrikDev unofficial API (free key: set HENRIK_API_KEY)
# Field names written from memory of the API docs; not verified offline.
# --------------------------------------------------------------------------
class ValorantProvider(Provider):
    key = "valorant"
    label = "HenrikDev (Valorant)"
    category = "Valorant"
    base = "https://api.henrikdev.xyz/valorant"

    def enabled(self):
        return bool(os.environ.get("HENRIK_API_KEY"))

    def get(self, path):
        return get_json(f"{self.base}/{path}", headers={"Authorization": os.environ.get("HENRIK_API_KEY", "")})

    def search(self, query):
        if "#" not in query:
            return []  # Riot IDs look like Name#TAG
        name, tag = (urllib.parse.quote(p.strip()) for p in query.split("#", 1))
        if not name or not tag:
            return []
        account = (self.get(f"v1/account/{name}/{tag}") or {}).get("data")
        if not account:
            return []
        player_id = f"{account.get('region', 'na')}/{account['name']}#{account['tag']}"
        return [self.result(player_id, f"{account['name']}#{account['tag']}",
                            f"Level {account.get('account_level', '?')} · {account.get('region', '').upper()}",
                            (account.get("card") or {}).get("small"))]

    def details(self, player_id):
        region, riot_id = player_id.split("/", 1)
        name, tag = (urllib.parse.quote(p) for p in riot_id.split("#", 1))
        account = (self.get(f"v1/account/{name}/{tag}") or {}).get("data")
        if not account:
            return None
        mmr = (self.get(f"v2/mmr/{region}/{name}/{tag}") or {}).get("data") or {}
        current = mmr.get("current_data") or {}
        highest = mmr.get("highest_rank") or {}
        rank_rows = [[k, v] for k, v in [
            ("Current rank", current.get("currenttierpatched")),
            ("Rank rating", current.get("ranking_in_tier")),
            ("Elo", current.get("elo")),
            ("Peak rank", highest.get("patched_tier")),
            ("Peak season", highest.get("season")),
        ] if v not in (None, "")]
        return profile(riot_id, self.category, (account.get("card") or {}).get("small"),
                       [section("Account", [["Level", account.get("account_level")], ["Region", region.upper()]]),
                        section("Competitive", rank_rows)],
                       [["tracker.gg", f"https://tracker.gg/valorant/profile/riot/{name}%23{tag}/overview"]],
                       None if rank_rows else "No competitive rank this act.")


# --------------------------------------------------------------------------
# Counter-Strike 2 (and other FACEIT games) - FACEIT Data API
# (free key: set FACEIT_API_KEY). Field names written from memory of the
# API docs; not verified offline.
# --------------------------------------------------------------------------
class FaceitProvider(Provider):
    key = "faceit"
    label = "FACEIT"
    category = "Counter-Strike 2 (FACEIT)"
    base = "https://open.faceit.com/data/v4"

    def enabled(self):
        return bool(os.environ.get("FACEIT_API_KEY"))

    def get(self, path, params=None):
        return get_json(f"{self.base}/{path}", params,
                        headers={"Authorization": f"Bearer {os.environ.get('FACEIT_API_KEY', '')}"})

    def search(self, query):
        data = self.get("search/players", {"nickname": query.strip(), "game": "cs2", "limit": 5}) or {}
        results = []
        for p in data.get("items", []):
            game = next((g for g in p.get("games", []) if g.get("name") == "cs2"), {})
            sub = " · ".join(filter(None, [f"Level {game['skill_level']}" if game.get("skill_level") else "",
                                           (p.get("country") or "").upper()]))
            results.append(self.result(p["player_id"], p.get("nickname", "?"), sub, p.get("avatar")))
        return results

    def details(self, player_id):
        player = self.get(f"players/{player_id}")
        if not player:
            return None
        cs2 = (player.get("games") or {}).get("cs2") or {}
        sections = [section("FACEIT rank", [[k, v] for k, v in [
            ("Skill level", cs2.get("skill_level")), ("Elo", cs2.get("faceit_elo")),
            ("Region", cs2.get("region"))] if v])]
        lifetime = (self.get(f"players/{player_id}/stats/cs2") or {}).get("lifetime") or {}
        sections.append(section("Lifetime CS2", pick(lifetime, [
            ("Matches", "Matches"), ("Wins", "Wins"), ("Win Rate %", "Win rate %"),
            ("Average K/D Ratio", "K/D"), ("Average Headshots %", "Headshot %"),
            ("Longest Win Streak", "Longest win streak"), ("Current Win Streak", "Current win streak")])))
        return profile(player.get("nickname", player_id), self.category, player.get("avatar"), sections,
                       [["FACEIT", f"https://www.faceit.com/en/players/{player.get('nickname', '')}"]],
                       None if lifetime else "No CS2 matches on FACEIT.")


# --------------------------------------------------------------------------
# Apex Legends - mozambiquehe.re (free key: set APEX_API_KEY)
# Field names written from memory of the API docs; not verified offline.
# --------------------------------------------------------------------------
class ApexProvider(Provider):
    key = "apex"
    label = "Apex Legends Status"
    category = "Apex Legends"
    PLATFORMS = ("PC", "PS4", "X1", "SWITCH")

    def enabled(self):
        return bool(os.environ.get("APEX_API_KEY"))

    def lookup(self, name, platform):
        data = get_json("https://api.mozambiquehe.re/bridge",
                        {"auth": os.environ.get("APEX_API_KEY", ""), "player": name, "platform": platform})
        # This API reports "player not found" as a 200 with an "Error" key.
        if not data or "Error" in data or not (data.get("global") or {}).get("name"):
            return None
        return data

    def search(self, query):
        name = query.strip()
        data = self.lookup(name, "PC")
        if not data:
            return []
        g = data["global"]
        rank = (g.get("rank") or {}).get("rankName")
        sub = " · ".join(filter(None, [f"Level {g.get('level')}" if g.get("level") else "", rank, "PC"]))
        return [self.result(f"PC/{g['name']}", g["name"], sub, (g.get("rank") or {}).get("rankImg"))]

    def details(self, player_id):
        platform, name = player_id.split("/", 1)
        if platform not in self.PLATFORMS:
            return None
        data = self.lookup(name, platform)
        if not data:
            return None
        g = data["global"]
        rank = g.get("rank") or {}
        sections = [section("Account", [[k, v] for k, v in [
            ("Level", g.get("level")), ("Platform", platform),
            ("Ranked", " ".join(filter(None, [rank.get("rankName"), str(rank.get("rankDiv") or "")])).strip()),
            ("Ranked points", rank.get("rankScore")),
        ] if v not in (None, "")])]
        totals = [[stat.get("name", key), stat.get("value")] for key, stat in (data.get("total") or {}).items()
                  if isinstance(stat, dict) and stat.get("value") not in (None, -1)]
        sections.append(section("Tracked totals", totals))
        selected = (data.get("legends") or {}).get("selected") or {}
        legend_rows = [[d.get("name", d.get("key")), d.get("value")] for d in selected.get("data") or []]
        if selected.get("LegendName"):
            sections.append(section(f"Selected legend: {selected['LegendName']}", legend_rows))
        return profile(g["name"], self.category, rank.get("rankImg"), sections,
                       [["apexlegendsstatus.com", f"https://apexlegendsstatus.com/profile/{platform}/{urllib.parse.quote(name)}"]],
                       "Apex only reports stats for the banner trackers a player has equipped.")


# --------------------------------------------------------------------------
# Everyone else (tennis, F1, boxing, cricket, CS, LoL pros...) - Wikipedia.
# Most athlete pages have an "infobox" with career numbers; we read those.
# --------------------------------------------------------------------------
INFOBOX_SKIP = {"image", "image_size", "imagesize", "caption", "alt", "signature", "module",
                "embed", "upright", "logo", "website", "footnotes", "medaltemplates", "name",
                "pcupdate", "ntupdate", "update", "updated", "image_upright", "landscape",
                "child", "fullname", "full_name", "signature_alt", "honorific_prefix",
                "honorific_suffix", "nickname", "native_name", "medals", "headercolor",
                "background", "module2", "module3", "pronunciation"}
INFOBOX_LABELS = {"currentclub": "Current club", "clubnumber": "Shirt number",
                  "careerprize": "Career prize money", "singlesrecord": "Singles record",
                  "singlestitles": "Singles titles", "highestsinglesranking": "Highest singles ranking",
                  "currentsinglesranking": "Current singles ranking", "doublesrecord": "Doubles record",
                  "doublestitles": "Doubles titles", "turnedpro": "Turned pro", "plays": "Plays",
                  "fastest_laps": "Fastest laps", "first_win": "First win", "last_win": "Last win",
                  "total_fights": "Total fights", "ko": "Wins by KO", "draft_year": "Draft year",
                  "draft_pick": "Draft pick", "nba_draft_year": "NBA draft year",
                  "career_start": "Career start", "career_end": "Career end",
                  "team_history": "Teams", "role": "Role", "game": "Game"}
CAREER_KEYS = {"years", "clubs", "caps", "goals", "youthyears", "youthclubs",
               "nationalyears", "nationalteam", "nationalcaps", "nationalgoals",
               "manageryears", "managerclubs"}


def split_infobox(wikitext):
    """Return {param: raw value} for the first {{Infobox ...}} in the page."""
    start = wikitext.lower().find("{{infobox")
    if start == -1:
        return {}
    parts, current, braces, brackets, i = [], [], 0, 0, start
    while i < len(wikitext):
        two = wikitext[i:i + 2]
        if two == "{{":
            braces += 1
        elif two == "}}":
            braces -= 1
            if braces == 0:
                parts.append("".join(current))
                break
        elif two == "[[":
            brackets += 1
        elif two == "]]":
            brackets -= 1
        if two in ("{{", "}}", "[[", "]]"):
            current.append(two)
            i += 2
            continue
        if wikitext[i] == "|" and braces == 1 and brackets == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(wikitext[i])
        i += 1
    params = {}
    for part in parts[1:]:
        if "=" in part:
            key, value = part.split("=", 1)
            params[key.strip().lower().replace(" ", "_")] = value
    return params


def _template(match):
    args = [a.strip() for a in match.group(1).split("|")]
    name = args[0].lower()
    plain = [a for a in args[1:] if "=" not in a]
    if name.startswith(("birth date", "death date", "start date", "end date", "dob")):
        nums = [a for a in plain if a.isdigit()][:3]
        return "-".join(n if i == 0 else n.zfill(2) for i, n in enumerate(nums))
    if name in ("nowrap", "nobr", "small", "abbr", "nbsp", "lang", "nowrap begin", "tooltip"):
        return plain[0] if plain else ""
    if name in ("ubl", "unbulleted list", "plainlist", "hlist", "flatlist", "ublist", "bulleted list"):
        return ", ".join(plain)
    if name in ("sortname",):
        return " ".join(plain[:2])
    if name in ("height",) and plain:
        return " ".join(plain)
    if name in ("convert", "cvt") and len(plain) >= 2:
        return f"{plain[0]} {plain[1]}"
    return ""


def clean_wikitext(value):
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"<ref[^>]*/>", "", value)
    value = re.sub(r"<ref[^>]*>.*?</ref>", "", value, flags=re.S)
    value = re.sub(r"<br\s*/?>", ", ", value)
    for _ in range(5):  # innermost templates first
        value, n = re.subn(r"\{\{([^{}]*)\}\}", _template, value)
        if not n:
            break
    value = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", value)
    value = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", value)
    value = re.sub(r"<[^>]+>", "", value)
    value = value.replace("'''", "").replace("''", "").replace("&nbsp;", " ")
    value = re.sub(r"\n\s*\*\s*", ", ", value)
    value = re.sub(r"\s+", " ", value).strip(" ,;")
    return value


def infobox_sections(params):
    facts, numbered = [], {}
    for key, raw in params.items():
        m = re.match(r"^([a-z_]+?)(\d+)$", key)
        if m and m.group(1) in CAREER_KEYS:
            numbered.setdefault(int(m.group(2)), {})[m.group(1)] = clean_wikitext(raw)
            continue
        if key in INFOBOX_SKIP or key.endswith(("_ref", "_alt", "_caption")):
            continue
        value = clean_wikitext(raw)
        if value and len(value) < 200:
            label = INFOBOX_LABELS.get(key) or key.replace("_", " ").strip().capitalize()
            facts.append([label, value])

    def career(prefix, team_key, caps_key, goals_key):
        rows = []
        for n in sorted(numbered):
            row = numbered[n]
            team = row.get(team_key)
            if not team:
                continue
            label = " ".join(filter(None, [row.get(prefix), team]))
            caps, goals = row.get(caps_key), row.get(goals_key)
            value = f"{caps} apps" if caps else ""
            if goals:
                value += f" ({goals} goals)"
            rows.append([label, value or "-"])
        return rows

    return [section("Career facts (Wikipedia infobox)", facts[:30]),
            section("Club career", career("years", "clubs", "caps", "goals")),
            section("International career", career("nationalyears", "nationalteam", "nationalcaps", "nationalgoals"))]


class WikipediaProvider(Provider):
    key = "wiki"
    label = "Wikipedia"
    category = "Wikipedia"
    SPORTY = ("player", "athlete", "footballer", "cricketer", "gamer", "esports",
              "racing", "driver", "boxer", "fighter", "tennis", "golfer", "swimmer",
              "runner", "sprinter", "skater", "wrestler", "cyclist", "olympi",
              "basketball", "baseball", "hockey", "quarterback", "chess", "coach",
              "jockey", "climber", "skier", "snowboarder", "gymnast", "rower", "darts",
              "snooker", "streamer", "artist", "mixed martial")

    def search(self, query):
        data = get_json("https://en.wikipedia.org/w/api.php", {
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": query, "gsrlimit": 10, "prop": "description|pageimages",
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
            if len(results) >= 4:
                break
        return results

    def details(self, player_id):
        title = urllib.parse.quote(player_id.replace(" ", "_"), safe="")
        data = get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
        if not data:
            return None
        sections = [{"title": "Summary", "text": data.get("extract", "")}]
        try:
            parsed = get_json("https://en.wikipedia.org/w/api.php", {
                "action": "parse", "page": player_id, "prop": "wikitext", "section": 0,
                "format": "json", "formatversion": 2, "redirects": 1}) or {}
            sections += infobox_sections(split_infobox(parsed.get("parse", {}).get("wikitext", "")))
        except requests.RequestException:
            pass  # the summary is still worth showing
        return profile(data.get("title", player_id), data.get("description", ""),
                       data.get("thumbnail", {}).get("source"), sections,
                       [["Wikipedia", data.get("content_urls", {}).get("desktop", {}).get(
                           "page", f"https://en.wikipedia.org/wiki/{title}")]],
                       "Stats come from the Wikipedia infobox, which editors update by hand, "
                       "so they can lag behind the latest games.")


PROVIDERS = [MLBProvider(), NHLProvider(), ESPNProvider(), OpenDotaProvider(), OverwatchProvider(),
             RiotProvider(), ValorantProvider(), FortniteProvider(), FaceitProvider(), ApexProvider(),
             ChessComProvider(), LichessProvider(), WikipediaProvider(), SportsDBProvider()]
BY_KEY = {p.key: p for p in PROVIDERS}


def active_providers():
    return [p for p in PROVIDERS if p.enabled()]
