#!/usr/bin/env python3
"""Read-only leaderboard for taiko-web."""

from collections import defaultdict
from datetime import datetime, timezone

from flask import Flask, abort, jsonify, redirect, render_template, request

import data
from data import (CROWN_IMPLIED, CROWN_LABEL, DIFF_COLOR, DIFF_LABEL,
                  DIFFICULTIES, db, recent_events, records, snapshot)

app = Flask(__name__)


class _StripHighscoresPrefix:
    """Accept the /highscores prefix that nginx normally strips.

    The site is served under /highscores/, and nginx rewrites
    ^/highscores/?(.*)$ to /$1 before proxying, so Flask itself only ever
    sees the bare path and the templates emit absolute /highscores/ URLs.
    Running `flask run` directly there is no nginx, so every link and the
    stylesheet would 404. Doing the same rewrite here makes the local
    server behave like the deployed one; in production no request ever
    arrives with the prefix still attached, so this never fires.
    """

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path == "/highscores" or path.startswith("/highscores/"):
            environ["PATH_INFO"] = path[len("/highscores"):] or "/"
        return self.wsgi_app(environ, start_response)


app.wsgi_app = _StripHighscoresPrefix(app.wsgi_app)
data.start_poller()


@app.context_processor
def globals_():
    return {"DIFFICULTIES": DIFFICULTIES, "DIFF_LABEL": DIFF_LABEL,
            "DIFF_COLOR": DIFF_COLOR, "CROWN_LABEL": CROWN_LABEL}


@app.template_filter("ago")
def ago(ts):
    """Compact relative time for the feed."""
    if not ts:
        return "\u2014"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    secs = (datetime.now(timezone.utc) - ts).total_seconds()
    for limit, div, unit in ((60, 1, "s"), (3600, 60, "m"),
                             (86400, 3600, "h"), (2592000, 86400, "d")):
        if secs < limit:
            return f"{int(secs // div)}{unit}" if secs >= 60 else "just now"
    return ts.strftime("%d %b")


def crown_standings(snap, diff=None):
    """Rank players by crowns collected, overall or at one difficulty.

    The crown counts are cumulative -- see CROWN_IMPLIED in data.py -- so
    a chart you full comboed is counted both as a full combo and as a
    clear, and a donderful counts as all three. Points are then the plain
    sum of the three, with nothing weighted.

    That comes to the same number the old weighting did, since counting a
    donderful once in each of three rows is what multiplying it by three
    was standing in for. It says it in a way a player can check, though:
    the score is the crowns, added up, rather than the crowns put through
    a table of what each is worth.

    The overall average place is an exact pooled mean, not an
    approximation: data.py divides each difficulty's total by its pool
    size, so multiplying back by that pool recovers the total and the
    sums combine cleanly across difficulties.
    """
    rows = []
    for u in snap["users"].values():
        if diff:
            d = u["per_diff"].get(diff)
            if not d or not d["pool"] or not d["plays"]:
                continue
            crowns, plays, pool = d["crowns"], d["plays"], d["pool"]
            firsts, avg = d["firsts"], d["avg_rank"]
        else:
            crowns, firsts = u["crowns"], u["firsts"]
            plays = pool = 0
            weighted = 0.0
            for per in u["per_diff"].values():
                if not per.get("pool"):
                    continue
                plays += per["plays"]
                pool += per["pool"]
                weighted += per["avg_rank"] * per["pool"]
            avg = weighted / pool if pool else 0.0

        rows.append({
            "name": u["name"], "crowns": crowns,
            # Every crown is at least a clear, so the clears are the count
            # of crowned charts.
            "total": crowns["silver"],
            "points": sum(crowns.values()),
            "plays": plays, "pool": pool, "firsts": firsts, "avg_rank": avg,
            "coverage": plays / pool * 100 if pool else 0.0,
        })

    rows.sort(key=lambda r: (-r["points"], -r["crowns"]["rainbow"], r["name"]))
    for i, r in enumerate(rows):
        r["place"] = i + 1
    return rows


def _find_song(snap, song_id):
    return next((s for s in snap["songs"].values() if s.get("id") == song_id), None)


# ------------------------------------------------------------------ pages

@app.route("/")
def index():
    snap = snapshot()
    unplayed = defaultdict(int)
    for diff, pool in snap["pools"].items():
        unplayed[diff] = len(pool)

    crown_diff = request.args.get("diff")
    if crown_diff and crown_diff not in DIFFICULTIES:
        abort(404)

    return render_template(
        "index.html", nav="index",
        feed=recent_events(40),
        newest_records=records(12),
        songs_ranked=sum(len(p) for p in snap["pools"].values()),
        players=len(snap["users"]),
        total_songs=len(snap["songs"]),
        standings=crown_standings(snap, crown_diff),
        crown_diff=crown_diff,
    )


@app.route("/browse")
@app.route("/browse/<diff>")
def browse(diff=None):
    snap = snapshot()
    if diff and diff not in DIFFICULTIES:
        abort(404)

    q = request.args.get("q", "").lower().strip()
    rows = []
    for h, song in snap["songs"].items():
        for d in ([diff] if diff else DIFFICULTIES):
            board = snap["boards"].get((h, d))
            if not board:
                continue
            if q and q not in (song["title"] + " " + (song.get("subtitle") or "")).lower():
                continue
            course = (song.get("courses") or {}).get(d) or {}
            rows.append({
                "song": song, "diff": d, "players": len(board),
                "leader": board[0], "stars": course.get("stars", 0),
                "cat": snap["cats"].get(song.get("category_id")) or {},
            })

    rows.sort(key=lambda r: (-r["players"], r["song"]["title"]))

    empty = []
    if diff:
        for h, song in snap["songs"].items():
            if (h, diff) not in snap["boards"] and (song.get("courses") or {}).get(diff):
                empty.append(song)

    return render_template("browse.html", nav="browse", rows=rows, diff=diff, q=q,
                           empty=sorted(empty, key=lambda s: s["title"])[:60],
                           empty_total=len(empty))


@app.route("/song/<int:song_id>")
def song(song_id):
    snap = snapshot()
    song = _find_song(snap, song_id)
    if not song:
        abort(404)

    boards = {}
    for d in DIFFICULTIES:
        board = snap["boards"].get((song["hash"], d))
        course = (song.get("courses") or {}).get(d)
        if board or course:
            boards[d] = {"rows": board or [],
                         "stars": (course or {}).get("stars", 0),
                         "branch": (course or {}).get("branch", False)}

    return render_template("song.html", nav="song", song=song, boards=boards,
                           cat=snap["cats"].get(song.get("category_id")) or {})


@app.route("/user/<name>")
def user(name):
    snap = snapshot()
    u = snap["users"].get(name)
    if not u:
        abort(404)

    diff_filter = request.args.get("diff")
    crown_filter = request.args.get("crown")
    # "or better" by default, matching the cumulative counts these links
    # are clicked from. "only" narrows to charts whose best crown is
    # exactly this one, which is the list of what to go back and improve:
    # a clear you have not full comboed, a full combo you have not made
    # donderful.
    crown_only = request.args.get("crown_mode") == "only"

    plays = []
    for (h, d), board in snap["boards"].items():
        row = next((r for r in board if r["user"] == name), None)
        if not row:
            continue
        if diff_filter and d != diff_filter:
            continue
        if crown_filter == "any":
            if not row["crown"]:
                continue
        elif crown_filter:
            if crown_only:
                if row["crown"] != crown_filter:
                    continue
            elif crown_filter not in CROWN_IMPLIED.get(row["crown"], ()):
                continue
        song = snap["songs"][h]
        plays.append({"song": song, "diff": d, "players": len(board),
                      "cat": snap["cats"].get(song.get("category_id")) or {},
                      "stars": ((song.get("courses") or {}).get(d) or {}).get("stars", 0),
                      **row})

    plays.sort(key=lambda p: (p["rank"], -p["points"]))

    genres = []
    for cid, n in sorted(u["genres"].items(), key=lambda kv: -kv[1]):
        cat = snap["cats"].get(cid)
        if cat:
            genres.append({"cat": cat, "count": n})

    return render_template("user.html", nav="user", u=u, plays=plays, genres=genres,
                           diff_filter=diff_filter, crown_filter=crown_filter,
                           crown_only=crown_only)


# -------------------------------------------------------------------- api
#
# Consumed by assets/custom.js, which injects a collapsible leaderboard
# panel into taiko-web itself. Same origin in production (both behind the
# one nginx), but the CORS header keeps local development working when
# the game is on mia and the leaderboard is on localhost.

@app.after_request
def _cors(resp):
    if request.path.startswith("/api/"):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/song/<int:song_id>")
def api_song(song_id):
    """Top of every difficulty board for one song."""
    snap = snapshot()
    song = _find_song(snap, song_id)
    if not song:
        return jsonify({"error": "not found"}), 404

    limit = min(int(request.args.get("limit", 5)), 25)
    boards = {}
    for d in DIFFICULTIES:
        board = snap["boards"].get((song["hash"], d))
        course = (song.get("courses") or {}).get(d)
        if not board and not course:
            continue
        boards[d] = {
            "label": DIFF_LABEL[d],
            "color": DIFF_COLOR[d],
            "stars": (course or {}).get("stars", 0),
            "players": len(board or []),
            "rows": [{"rank": r["rank"], "user": r["user"], "points": r["points"],
                      "accuracy": round(r["accuracy"], 1), "crown": r["crown"],
                      "good": r["good"], "ok": r["ok"], "bad": r["bad"],
                      "maxCombo": r["maxCombo"]}
                     for r in (board or [])[:limit]],
        }

    return jsonify({"id": song_id, "title": song["title"],
                    "subtitle": song.get("subtitle"),
                    "url": f"/highscores/song/{song_id}", "boards": boards})


@app.route("/api/user/<name>")
def api_user(name):
    """Summary card for one player."""
    snap = snapshot()
    u = snap["users"].get(name)
    if not u:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "name": u["name"], "plays": u["plays"], "firsts": u["firsts"],
        "crowns": u["crowns"],
        "per_diff": {d: {"plays": s["plays"], "pool": s["pool"],
                         "firsts": s["firsts"],
                         "avg_rank": round(s["avg_rank"], 2),
                         "coverage": round(s["coverage"], 1),
                         "crowns": s["crowns"]}
                     for d, s in u["per_diff"].items() if s.get("pool")},
        "url": f"/highscores/user/{name}",
    })


@app.route("/api/recent")
def api_recent():
    """The score feed, for anything that wants to show it elsewhere."""
    limit = min(int(request.args.get("limit", 20)), 100)
    out = []
    for e in recent_events(limit):
        out.append({
            "user": e["user"], "song": e["song"]["title"],
            "song_id": e["song"].get("id"), "diff": e["diff"],
            "diff_label": DIFF_LABEL.get(e["diff"], e["diff"]),
            "rank": e.get("rank"), "players": e.get("players"),
            "points": e["points"], "accuracy": round(e.get("accuracy", 0), 1),
            "crown": e.get("crown"),
            "ts": e["ts"].isoformat() if e.get("ts") else None,
            "historic": e.get("historic", False),
        })
    return jsonify(out)


# ------------------------------------------------------------------ local

@app.route("/assets/<path:p>")
def _local_assets(p):
    """Borrow the game art from the live site when running locally.

    In the real deployment nginx matches ^/(assets|songs|src)/ and serves
    those files straight from disk, so a request never reaches Flask and
    this route is dead code. It only fires under `flask run`, where there
    is no nginx in front and /assets/img/*.png would otherwise 404 and
    leave every difficulty sprite, crown and Don-chan layer blank.
    """
    return redirect(f"http://mia:34800/assets/{p}")


@app.route("/health")
def health():
    return {"scores": db.scores.count_documents({}),
            "events": db.hs_events.count_documents({})}
