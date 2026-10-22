"""Offline tests: every API call is replaced with a fake response.

Run from the player_stats folder:
    python -m unittest discover tests
"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import providers  # noqa: E402
from app import app  # noqa: E402

FAKE = {
    "statsapi.mlb.com/api/v1/people/search": {"people": [
        {"id": 592450, "fullName": "Aaron Judge",
         "primaryPosition": {"abbreviation": "RF"}, "currentTeam": {"name": "New York Yankees"}}]},
    "statsapi.mlb.com/api/v1/people/592450": {"people": [{
        "id": 592450, "fullName": "Aaron Judge", "birthDate": "1992-04-26",
        "primaryPosition": {"name": "Outfielder"}, "currentTeam": {"name": "New York Yankees"},
        "batSide": {"code": "R"}, "pitchHand": {"code": "R"},
        "stats": [
            {"type": {"displayName": "yearByYear"}, "group": {"displayName": "hitting"},
             "splits": [{"season": "2023", "stat": {"homeRuns": 37}},
                        {"season": "2024", "team": {"name": "New York Yankees"},
                         "stat": {"homeRuns": 58, "avg": ".322"}}]},
            {"type": {"displayName": "career"}, "group": {"displayName": "hitting"},
             "splits": [{"stat": {"gamesPlayed": 1000, "homeRuns": 315, "avg": ".288"}}]},
        ]}]},
    "search.d3.nhle.com/api/v1/search/player": [
        {"playerId": "8478402", "name": "Connor McDavid", "positionCode": "C",
         "teamAbbrev": "EDM", "active": True}],
    "api-web.nhle.com/v1/player/8478402/landing": {
        "firstName": {"default": "Connor"}, "lastName": {"default": "McDavid"},
        "position": "C", "fullTeamName": {"default": "Edmonton Oilers"},
        "headshot": "https://example.com/mcdavid.png",
        "careerTotals": {"regularSeason": {"gamesPlayed": 700, "goals": 350, "assists": 650, "points": 1000}},
        "featuredStats": {"season": 20242025,
                          "regularSeason": {"subSeason": {"gamesPlayed": 67, "points": 100}}}},
    "api.opendota.com/api/proPlayers": [
        {"account_id": 105248644, "name": "Miracle-", "team_name": "Nigma", "country_code": "jo"},
        {"account_id": 1, "name": "Someone Else"}],
    "api.opendota.com/api/players/105248644": {
        "profile": {"personaname": "Miracle-", "name": "Miracle-", "avatarfull": None},
        "rank_tier": 80, "leaderboard_rank": 12},
    "api.opendota.com/api/players/105248644/wl": {"win": 600, "lose": 400},
    "api.opendota.com/api/players/105248644/heroes": [
        {"hero_id": 1, "games": 100, "win": 60}, {"hero_id": 2, "games": 0, "win": 0}],
    "api.opendota.com/api/heroes": [{"id": 1, "localized_name": "Anti-Mage"}],
    "api.chess.com/pub/player/hikaru": {
        "username": "hikaru", "name": "Hikaru Nakamura", "title": "GM", "url": "https://www.chess.com/member/Hikaru"},
    "api.chess.com/pub/player/hikaru/stats": {
        "chess_blitz": {"last": {"rating": 3300}, "best": {"rating": 3400},
                        "record": {"win": 10, "loss": 2, "draw": 3}}},
    "lichess.org/api/player/autocomplete": {"result": [{"id": "drnykterstein", "name": "DrNykterstein", "title": "GM"}]},
    "lichess.org/api/user/drnykterstein": {
        "username": "DrNykterstein", "title": "GM",
        "perfs": {"bullet": {"games": 500, "rating": 3200}, "rapid": {"games": 0, "rating": 1500}},
        "count": {"all": 600, "win": 450, "loss": 100, "draw": 50}},
    "www.thesportsdb.com/api/v1/json/3/searchplayers.php": {"player": [
        {"idPlayer": "34146370", "strPlayer": "Lionel Messi", "strSport": "Soccer",
         "strTeam": "Inter Miami", "strPosition": "Forward"}]},
    "www.thesportsdb.com/api/v1/json/3/lookupplayer.php": {"players": [
        {"idPlayer": "34146370", "strPlayer": "Lionel Messi", "strSport": "Soccer",
         "strNationality": "Argentina", "strDescriptionEN": "Argentine footballer."}]},
    "en.wikipedia.org/w/api.php": {"query": {"pages": {
        "1": {"index": 1, "title": "Faker (gamer)", "description": "South Korean esports player"},
        "2": {"index": 2, "title": "Faker", "description": "Disambiguation page"}}}},
    "en.wikipedia.org/api/rest_v1/page/summary/Faker_%28gamer%29": {
        "title": "Faker (gamer)", "description": "South Korean esports player", "extract": "Lee Sang-hyeok..."},
    "en.wikipedia.org/api/rest_v1/page/summary/Lionel_Messi": {
        "title": "Lionel Messi", "description": "Argentine footballer", "extract": "Messi is..."},
    "site.web.api.espn.com/apis/common/v3/search": {"items": [
        {"id": "1966", "type": "player", "displayName": "LeBron James",
         "uid": "s:40~l:46~a:1966", "description": "Los Angeles Lakers"},
        {"id": "33039", "type": "player", "displayName": "Some MLB Guy", "sport": "baseball", "league": "mlb"},
        {"id": "9", "type": "team", "displayName": "Not a player", "uid": "s:40~l:46~t:13"}]},
    "site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/1966": {"athlete": {
        "displayName": "LeBron James", "team": {"displayName": "Los Angeles Lakers"},
        "position": {"displayName": "Small Forward"}, "jersey": "23",
        "headshot": {"href": "https://example.com/lebron.png"}}},
    "site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/1966/overview": {"statistics": {
        "labels": ["GP", "PTS", "REB", "AST"],
        "displayNames": ["Games Played", "Points Per Game", "Rebounds Per Game", "Assists Per Game"],
        "splits": [{"displayName": "Regular Season", "stats": ["70", "25.7", "7.3", "8.3"]},
                   {"displayName": "Career", "stats": ["1492", "27.1", "7.5", "7.4"]}]}},
    "americas.api.riotgames.com/riot/account/v1/accounts/by-riot-id/Faker/KR1": {
        "puuid": "abc-123", "gameName": "Faker", "tagLine": "KR1"},
    "americas.api.riotgames.com/riot/account/v1/accounts/by-puuid/abc-123": {
        "puuid": "abc-123", "gameName": "Faker", "tagLine": "KR1"},
    "na1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/abc-123": {"summonerLevel": 900, "profileIconId": 6},
    "na1.api.riotgames.com/lol/league/v4/entries/by-puuid/abc-123": [
        {"queueType": "RANKED_SOLO_5x5", "tier": "CHALLENGER", "rank": "I", "leaguePoints": 1500,
         "wins": 300, "losses": 200}],
    "na1.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/abc-123/top": [
        {"championId": 7, "championLevel": 50, "championPoints": 1234567}],
    "overfast-api.tekrop.fr/players": {"total": 1, "results": [
        {"player_id": "TeKrop-2217", "name": "TeKrop#2217", "avatar": None, "is_public": True}]},
    "overfast-api.tekrop.fr/players/TeKrop-2217/summary": {
        "username": "TeKrop", "avatar": None, "endorsement": {"level": 3},
        "competitive": {"pc": {"season": 9, "tank": None,
                               "damage": {"division": "diamond", "tier": 2}, "support": None, "open": None},
                        "console": None}},
    "overfast-api.tekrop.fr/players/TeKrop-2217/stats/summary": {
        "general": {"games_played": 200, "games_won": 110, "winrate": 55.0, "kda": 3.1,
                    "time_played": 360000, "average": {"eliminations": 18.2, "damage": 9000}},
        "roles": {"damage": {"games_played": 150, "winrate": 56.0}, "tank": None},
        "heroes": {"soldier-76": {"games_played": 80, "winrate": 60, "time_played": 100},
                   "cassidy": {"games_played": 40, "winrate": 50, "time_played": 50}}},
    "fortnite-api.com/v2/stats/br/v2": {"status": 200, "data": {
        "account": {"id": "x", "name": "Ninja"}, "battlePass": {"level": 120, "progress": 40},
        "stats": {"all": {"overall": {"matches": 1000, "wins": 300, "winRate": 30.0, "kills": 5000, "kd": 7.14},
                          "solo": {"matches": 400, "wins": 100}}}}},
    "api.henrikdev.xyz/valorant/v1/account/TenZ/0505": {"status": 200, "data": {
        "name": "TenZ", "tag": "0505", "region": "na", "account_level": 400, "card": {"small": None}}},
    "api.henrikdev.xyz/valorant/v2/mmr/na/TenZ/0505": {"status": 200, "data": {
        "current_data": {"currenttierpatched": "Radiant", "ranking_in_tier": 700, "elo": 3100},
        "highest_rank": {"patched_tier": "Radiant", "season": "e9a1"}}},
    "open.faceit.com/data/v4/search/players": {"items": [
        {"player_id": "fc-1", "nickname": "s1mple", "country": "ua",
         "games": [{"name": "cs2", "skill_level": 10}]}]},
    "open.faceit.com/data/v4/players/fc-1": {"player_id": "fc-1", "nickname": "s1mple",
                                             "games": {"cs2": {"skill_level": 10, "faceit_elo": 3500}}},
    "open.faceit.com/data/v4/players/fc-1/stats/cs2": {"lifetime": {
        "Matches": "900", "Win Rate %": "64", "Average K/D Ratio": "1.45", "Average Headshots %": "41"}},
    "ddragon.leagueoflegends.com/api/versions.json": ["15.1.1"],
    "ddragon.leagueoflegends.com/cdn/15.1.1/data/en_US/champion.json": {
        "data": {"Leblanc": {"key": "7", "name": "LeBlanc"}}},
}

# A trimmed copy of the start of a real Wikipedia football article.
MESSI_WIKITEXT = """{{Short description|Argentine footballer}}
{{Infobox football biography
| name = Lionel Messi
| image = Lionel Messi 2022.jpg
| caption = Messi with Argentina in 2022
| birth_date = {{birth date and age|1987|6|24|df=y}}
| birth_place = [[Rosario, Santa Fe|Rosario]], Argentina
| height = 1.70 m<ref>{{cite web|url=http://x.com}}</ref>
| position = [[Forward (association football)|Forward]]
| currentclub = [[Inter Miami CF|Inter Miami]]
| years1 = 2004–2021 | clubs1 = [[FC Barcelona|Barcelona]] | caps1 = 520 | goals1 = 474
| years2 = 2021–2023 | clubs2 = [[Paris Saint-Germain F.C.|Paris Saint-Germain]] | caps2 = 58 | goals2 = 22
| nationalyears1 = 2005– | nationalteam1 = [[Argentina national football team|Argentina]]
| nationalcaps1 = 191 | nationalgoals1 = 112
| medaltemplates = {{MedalSport|Men's football}}
}}
'''Lionel Andres Messi''' is an Argentine footballer."""


def fake_get_json(url, params=None, cache_seconds=None, headers=None):
    key = url.split("://", 1)[1]
    if "riotgames.com" in key:
        assert headers and headers.get("X-Riot-Token"), "Riot calls must send the API key"
    if any(host in key for host in ("fortnite-api.com", "henrikdev.xyz", "faceit.com")):
        assert headers and headers.get("Authorization"), "keyed APIs must send the key"
    if key == "en.wikipedia.org/w/api.php" and (params or {}).get("action") == "parse":
        text = MESSI_WIKITEXT if params["page"] == "Lionel Messi" else "No infobox here."
        return {"parse": {"wikitext": text}}
    if key not in FAKE and "chess.com" in key:
        return None  # unknown username -> 404
    if key not in FAKE:
        raise AssertionError(f"Unexpected URL in test: {url}")
    return FAKE[key]


class ProviderTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(providers, "get_json", side_effect=fake_get_json)
        patcher.start()
        self.addCleanup(patcher.stop)

    def rows(self, profile, title):
        block = next(s for s in profile["sections"] if s["title"] == title)
        return dict(block["rows"])

    def test_mlb(self):
        p = providers.MLBProvider()
        [hit] = p.search("judge")
        self.assertEqual(hit["name"], "Aaron Judge")
        self.assertIn("RF", hit["subtitle"])
        prof = p.details("592450")
        self.assertEqual(prof["sections"][0]["title"], "Bio")
        self.assertEqual(self.rows(prof, "Career hitting")["Home runs"], 315)
        self.assertEqual(self.rows(prof, "2024 hitting (New York Yankees)")["Home runs"], 58)
        self.assertEqual(self.rows(prof, "Bio")["Bats / Throws"], "R/R")

    def test_nhl(self):
        p = providers.NHLProvider()
        [hit] = p.search("mcdavid")
        self.assertEqual(hit["id"], "8478402")
        prof = p.details("8478402")
        self.assertEqual(prof["name"], "Connor McDavid")
        self.assertEqual(self.rows(prof, "Career regular season")["Points"], 1000)
        self.assertEqual(self.rows(prof, "2024-2025 season")["Points"], 100)

    def test_dota(self):
        p = providers.OpenDotaProvider()
        [hit] = p.search("miracle")
        self.assertEqual(hit["id"], "105248644")
        prof = p.details("105248644")
        overview = self.rows(prof, "Overview")
        self.assertEqual(overview["Win rate"], "60.0%")
        self.assertEqual(overview["Rank"], "Immortal")
        self.assertEqual(self.rows(prof, "Most played heroes"), {"Anti-Mage": "100 games · 60% wins"})

    def test_dota_rank_with_stars(self):
        self.assertEqual(providers.OpenDotaProvider().rank(54), "Legend 4")

    def test_chesscom(self):
        p = providers.ChessComProvider()
        self.assertEqual(p.search("Hikaru")[0]["name"], "Hikaru Nakamura")
        self.assertEqual(p.search("not a real user"), [])
        self.assertEqual(p.search("drop table;"), [])
        prof = p.details("hikaru")
        self.assertEqual(self.rows(prof, "Blitz")["Best rating"], 3400)

    def test_lichess(self):
        p = providers.LichessProvider()
        self.assertEqual(p.search("drnyk")[0]["id"], "drnykterstein")
        self.assertEqual(p.search("ab"), [])  # too short, no request made
        prof = p.details("drnykterstein")
        ratings = self.rows(prof, "Ratings")
        self.assertIn("Bullet", ratings)
        self.assertNotIn("Rapid", ratings)  # 0 games -> hidden

    def test_sportsdb(self):
        p = providers.SportsDBProvider()
        [hit] = p.search("messi")
        self.assertEqual(hit["category"], "Soccer")
        self.assertFalse(hit["has_stats"])
        prof = p.details("34146370")
        self.assertEqual(self.rows(prof, "Profile")["Nationality"], "Argentina")

    def test_espn(self):
        p = providers.ESPNProvider()
        results = p.search("lebron")
        self.assertEqual([r["name"] for r in results], ["LeBron James"])  # MLB guy + team skipped
        self.assertEqual(results[0]["id"], "basketball/nba/1966")
        self.assertEqual(results[0]["category"], "Basketball (NBA)")
        prof = p.details("basketball/nba/1966")
        self.assertEqual(self.rows(prof, "Career")["Points Per Game"], "27.1")
        self.assertEqual(self.rows(prof, "Bio")["Number"], "23")
        self.assertIsNone(p.details("not-a-valid-id"))

    def test_espn_flat_stats_and_core_api_fallback(self):
        p = providers.ESPNProvider()
        flat = {"labels": ["GP", "PTS"], "displayValues": ["56", "26.4"]}
        [block] = p.stat_sections(flat)
        self.assertEqual(block["rows"], [["GP", "56"], ["PTS", "26.4"]])

        core = "sports.core.api.espn.com/v2/sports/basketball/leagues/nba/athletes/3975"
        extra = {core: {"displayName": "Stephen Curry", "jersey": "30"},
                 "site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/3975/overview":
                     {"statistics": flat}}

        def fake(url, params=None, cache_seconds=None, headers=None):
            key = url.split("://", 1)[1]
            if key == "site.web.api.espn.com/apis/common/v3/sports/basketball/nba/athletes/3975":
                return None  # common v3 bio missing -> use Core API
            return extra[key]
        with mock.patch.object(providers, "get_json", side_effect=fake):
            prof = p.details("basketball/nba/3975")
        self.assertEqual(prof["name"], "Stephen Curry")
        self.assertEqual(self.rows(prof, "Current season")["PTS"], "26.4")

    def test_espn_search_v2_fallback(self):
        v2 = {"results": [{"type": "team", "contents": []}, {"type": "player", "contents": [
            {"displayName": "Patrick Mahomes", "uid": "s:20~l:28~a:3139477",
             "subtitle": "Kansas City Chiefs", "image": {"default": "https://example.com/pm.png"}}]}]}

        def fake(url, params=None, cache_seconds=None, headers=None):
            return v2 if url.endswith("/search/v2") else {"items": []}
        with mock.patch.object(providers, "get_json", side_effect=fake):
            [hit] = providers.ESPNProvider().search("mahomes")
        self.assertEqual(hit["id"], "football/nfl/3139477")
        self.assertEqual(hit["category"], "American football (NFL)")

    def test_overwatch(self):
        p = providers.OverwatchProvider()
        [hit] = p.search("TeKrop")
        self.assertEqual(hit["id"], "TeKrop-2217")
        self.assertEqual(p.search("two words"), [])
        prof = p.details("TeKrop-2217")
        self.assertEqual(self.rows(prof, "Competitive rank"), {"Damage (PC)": "Diamond 2"})
        overall = self.rows(prof, "All heroes")
        self.assertEqual(overall["Win rate"], "55.0%")
        self.assertEqual(overall["Hours played"], 100.0)
        self.assertEqual(list(self.rows(prof, "Most played heroes")), ["Soldier 76", "Cassidy"])

    def test_keyed_game_providers_off_without_keys(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            for cls in (providers.FortniteProvider, providers.ValorantProvider, providers.FaceitProvider):
                self.assertFalse(cls().enabled(), cls.__name__)

    def test_fortnite(self):
        with mock.patch.dict(os.environ, {"FORTNITE_API_KEY": "k"}):
            p = providers.FortniteProvider()
            [hit] = p.search("Ninja")
            prof = p.details(hit["id"])
        self.assertEqual(self.rows(prof, "Overall")["K/D"], 7.14)
        self.assertEqual(self.rows(prof, "Battle pass")["Level"], 120)

    def test_valorant(self):
        with mock.patch.dict(os.environ, {"HENRIK_API_KEY": "k"}):
            p = providers.ValorantProvider()
            self.assertEqual(p.search("TenZ"), [])
            [hit] = p.search("TenZ#0505")
            prof = p.details(hit["id"])
        self.assertEqual(hit["id"], "na/TenZ#0505")
        self.assertEqual(self.rows(prof, "Competitive")["Current rank"], "Radiant")

    def test_faceit(self):
        with mock.patch.dict(os.environ, {"FACEIT_API_KEY": "k"}):
            p = providers.FaceitProvider()
            [hit] = p.search("s1mple")
            prof = p.details(hit["id"])
        self.assertEqual(hit["subtitle"], "Level 10 · UA")
        self.assertEqual(self.rows(prof, "Lifetime CS2")["K/D"], "1.45")
        self.assertEqual(self.rows(prof, "FACEIT rank")["Elo"], 3500)

    def test_apex(self):
        data = {"global": {"name": "ImperialHal", "level": 500,
                           "rank": {"rankName": "Predator", "rankDiv": 0, "rankScore": 30000}},
                "total": {"kills": {"name": "BR Kills", "value": 50000}, "damage": {"name": "Damage", "value": -1}},
                "legends": {"selected": {"LegendName": "Bangalore",
                                         "data": [{"name": "BR Kills", "value": 9000, "key": "kills"}]}}}

        def fake(url, params=None, cache_seconds=None, headers=None):
            self.assertTrue(params.get("auth"))
            return data if params["player"] == "ImperialHal" else {"Error": "Player not found"}
        with mock.patch.dict(os.environ, {"APEX_API_KEY": "k"}), \
                mock.patch.object(providers, "get_json", side_effect=fake):
            p = providers.ApexProvider()
            self.assertEqual(p.search("nobody"), [])
            [hit] = p.search("ImperialHal")
            prof = p.details(hit["id"])
            self.assertIsNone(p.details("XBOX360/ImperialHal"))
        self.assertEqual(self.rows(prof, "Account")["Ranked"], "Predator")
        self.assertEqual(self.rows(prof, "Tracked totals"), {"BR Kills": 50000})  # -1 = not tracked
        self.assertEqual(self.rows(prof, "Selected legend: Bangalore"), {"BR Kills": 9000})

    def test_riot_disabled_without_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(providers.RiotProvider().enabled())

    def test_riot_with_key(self):
        with mock.patch.dict(os.environ, {"RIOT_API_KEY": "test-key"}):
            p = providers.RiotProvider()
            self.assertEqual(p.search("Faker"), [])  # needs Name#TAG
            [hit] = p.search("Faker#KR1")
            prof = p.details(hit["id"])
        solo = self.rows(prof, "Ranked Solo/Duo")
        self.assertEqual(solo["Rank"], "Challenger I")
        self.assertEqual(solo["Win rate"], "60.0%")
        self.assertEqual(self.rows(prof, "Top champions (mastery)"),
                         {"LeBlanc": "Level 50 · 1,234,567 pts"})

    def test_wikipedia_infobox_stats(self):
        prof = providers.WikipediaProvider().details("Lionel Messi")
        facts = self.rows(prof, "Career facts (Wikipedia infobox)")
        self.assertEqual(facts["Birth date"], "1987-06-24")
        self.assertEqual(facts["Birth place"], "Rosario, Argentina")
        self.assertEqual(facts["Height"], "1.70 m")
        self.assertEqual(facts["Position"], "Forward")
        self.assertNotIn("Image", facts)
        self.assertNotIn("Medaltemplates", facts)
        self.assertEqual(self.rows(prof, "Club career"), {
            "2004–2021 Barcelona": "520 apps (474 goals)",
            "2021–2023 Paris Saint-Germain": "58 apps (22 goals)"})
        self.assertEqual(self.rows(prof, "International career"),
                         {"2005– Argentina": "191 apps (112 goals)"})

    def test_wikipedia_filters_non_athletes(self):
        p = providers.WikipediaProvider()
        results = p.search("faker")
        self.assertEqual([r["name"] for r in results], ["Faker (gamer)"])
        prof = p.details("Faker (gamer)")
        self.assertIn("Lee Sang-hyeok", prof["sections"][0]["text"])


class RouteTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(providers, "get_json", side_effect=fake_get_json)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app.test_client()

    def test_home_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Player Stats Search", res.data)

    def test_search_merges_sources_and_reports_failures(self):
        with mock.patch.object(providers.MLBProvider, "search", side_effect=ConnectionError):
            data = self.client.get("/api/search?q=miracle").get_json()
        names = [r["name"] for r in data["results"]]
        self.assertIn("Miracle-", names)
        self.assertIn({"source": "MLB Stats API", "error": "ConnectionError"}, data["errors"])
        # Dedicated APIs first, then Wikipedia, then TheSportsDB profiles.
        order = [{"wiki": 1, "sportsdb": 2}.get(r["source"], 0) for r in data["results"]]
        self.assertEqual(order, sorted(order))

    def test_disabled_source_is_404(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.client.get("/api/player/lol/abc-123").status_code, 404)

    def test_search_too_short(self):
        data = self.client.get("/api/search?q=a").get_json()
        self.assertEqual(data["results"], [])

    def test_player_route(self):
        data = self.client.get("/api/player/nhl/8478402").get_json()
        self.assertEqual(data["name"], "Connor McDavid")
        self.assertEqual(data["source_label"], "NHL API")

    def test_player_route_with_slash_like_id(self):
        res = self.client.get("/api/player/wiki/Faker%20(gamer)")
        self.assertEqual(res.status_code, 200)

    def test_unknown_source(self):
        self.assertEqual(self.client.get("/api/player/nope/1").status_code, 404)

    def test_player_not_found(self):
        self.assertEqual(self.client.get("/api/player/chesscom/nobody123").status_code, 404)


if __name__ == "__main__":
    unittest.main()
