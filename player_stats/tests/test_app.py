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
}


def fake_get_json(url, params=None, cache_seconds=None):
    key = url.split("://", 1)[1]
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
        # Results with real stats come before bio-only ones.
        flags = [r["has_stats"] for r in data["results"]]
        self.assertEqual(flags, sorted(flags, reverse=True))

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
