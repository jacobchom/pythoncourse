"""Live check: does every source actually return a real player's stats?

The tests in tests/ use fake data, so they can't tell you whether an API has
changed. Run this on a machine with internet access:

    python check_sources.py            # check every enabled source
    python check_sources.py espn ow    # check just some

For each source it searches for a well-known player, opens the first result,
and counts the stat rows that came back.
"""

import sys
import time

import providers

SAMPLES = {
    "mlb": "Aaron Judge",
    "nhl": "Connor McDavid",
    "espn": "LeBron James",
    "dota": "Miracle",
    "ow": "TeKrop",
    "lol": "Agurin#EUW",
    "valorant": "TenZ#0505",
    "fortnite": "Ninja",
    "faceit": "s1mple",
    "apex": "ImperialHal",
    "chesscom": "hikaru",
    "lichess": "DrNykterstein",
    "wiki": "Novak Djokovic",
    "sportsdb": "Lionel Messi",
}


def check(provider):
    query = SAMPLES.get(provider.key)
    if not query:
        return "SKIP", "no sample player"
    start = time.time()
    try:
        results = provider.search(query)
    except Exception as exc:
        return "FAIL", f"search error: {type(exc).__name__}: {exc}"
    if not results:
        return "FAIL", f"search for {query!r} returned nothing"
    first = results[0]
    try:
        data = provider.details(first["id"])
    except Exception as exc:
        return "FAIL", f"found {first['name']!r} but details error: {type(exc).__name__}: {exc}"
    if not data:
        return "FAIL", f"found {first['name']!r} but details came back empty"
    rows = sum(len(s.get("rows", [])) for s in data["sections"])
    status = "OK" if rows else "WARN"
    return status, f"{first['name']!r}: {len(data['sections'])} sections, {rows} stat rows ({time.time() - start:.1f}s)"


def main(keys):
    chosen = [p for p in providers.PROVIDERS if not keys or p.key in keys]
    failures = 0
    for provider in chosen:
        if not provider.enabled():
            print(f"{'OFF':5} {provider.label:28} no API key set")
            continue
        status, detail = check(provider)
        failures += status == "FAIL"
        print(f"{status:5} {provider.label:28} {detail}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
