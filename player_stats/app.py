"""Player stats search - a small Flask website.

Run it with:
    pip install -r requirements.txt
    python app.py
then open http://127.0.0.1:5000
"""

from concurrent.futures import ThreadPoolExecutor, wait

from flask import Flask, jsonify, render_template, request

from providers import BY_KEY, PROVIDERS, active_providers

app = Flask(__name__)
pool = ThreadPoolExecutor(max_workers=len(PROVIDERS))
SEARCH_DEADLINE = 12  # seconds to wait for all sources before giving up on slow ones


@app.route("/")
def index():
    return render_template("index.html", providers=active_providers())


@app.route("/api/search")
def search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"query": query, "results": [], "errors": [],
                        "message": "Type at least 2 characters."})

    wanted = request.args.get("sources")
    providers = active_providers()
    if wanted:
        providers = [p for p in providers if p.key in wanted.split(",")]

    # Ask every source at the same time so one slow API doesn't block the rest.
    futures = {pool.submit(p.search, query): p for p in providers}
    done, not_done = wait(futures, timeout=SEARCH_DEADLINE)

    results, errors = [], []
    for future in futures:
        provider = futures[future]
        if future in not_done:
            errors.append({"source": provider.label, "error": "timed out"})
            continue
        try:
            results.extend(future.result())
        except Exception as exc:  # one broken API shouldn't break the whole search
            errors.append({"source": provider.label, "error": type(exc).__name__})

    # Dedicated stats APIs first, then Wikipedia, then profile-only sources;
    # within each group exact name matches come first.
    q = query.lower()
    tier = {"wiki": 1, "sportsdb": 2}
    results.sort(key=lambda r: (tier.get(r["source"], 0), r["name"].lower() != q))
    return jsonify({"query": query, "results": results, "errors": errors})


@app.route("/api/player/<source>/<path:player_id>")
def player(source, player_id):
    provider = BY_KEY.get(source)
    if not provider or not provider.enabled():
        return jsonify({"error": f"Unknown source '{source}'"}), 404
    try:
        data = provider.details(player_id)
    except Exception as exc:
        return jsonify({"error": f"{provider.label} failed: {type(exc).__name__}"}), 502
    if not data:
        return jsonify({"error": "Player not found"}), 404
    data["source_label"] = provider.label
    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
