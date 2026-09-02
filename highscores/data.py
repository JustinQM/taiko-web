"""Score decoding, aggregation and history tracking for the leaderboard."""

import os
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone

from pymongo import MongoClient

DIFFICULTIES = ["easy", "normal", "hard", "oni", "ura"]
DIFF_LABEL = {"easy": "Easy", "normal": "Normal", "hard": "Hard",
              "oni": "Extreme", "ura": "Inner Extreme"}
DIFF_COLOR = {"easy": "#f76c1f", "normal": "#8fbf3f", "hard": "#5b8fd4",
              "oni": "#c8386e", "ura": "#7a3fb8"}
# order in the stored string, which is NOT the display order
STORED_ORDER = ["oni", "ura", "hard", "normal", "easy"]
SCORE_KEYS = ["points", "good", "ok", "bad", "maxCombo", "drumroll"]
CROWNS = ["", "silver", "gold", "rainbow"]
CROWN_LABEL = {"silver": "Clear", "gold": "Full Combo", "rainbow": "Donderful Combo"}

_client = MongoClient(os.environ.get("MONGO_URL", "mongodb://mongo:27017"))
db = _client[os.environ.get("MONGO_DB", "taiko")]

POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "60"))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", "20"))


def decode(raw):
    """Stored format: difficulties separated by ';', in STORED_ORDER.
    Each is a crown digit followed by six base36 values."""
    out = {}
    for i, chunk in enumerate(raw.split(";")):
        if not chunk or i >= len(STORED_ORDER):
            continue
        try:
            crown = CROWNS[int(chunk[0])]
            rest = chunk[1:]
        except (ValueError, IndexError):
            crown, rest = "", chunk
        entry = {}
        for k, v in zip(SCORE_KEYS, rest.split(",")):
            try:
                entry[k] = int(v, 36)
            except ValueError:
                entry[k] = 0
        if not entry.get("points"):
            continue
        entry["crown"] = crown
        total = entry["good"] + entry["ok"] + entry["bad"]
        entry["accuracy"] = (entry["good"] + entry["ok"] * 0.5) / total * 100 if total else 0.0
        out[STORED_ORDER[i]] = entry
    return out


# ---------------------------------------------------------------- history

def poll_once(emit=True):
    """Diff the scores collection against our snapshot.

    taiko-web upserts one document per (user, song) holding every
    difficulty, so the document's _id timestamp is the first time that
    user touched the song — useless as a feed clock. We keep our own.

    With emit=False the snapshot is seeded without recording events,
    which is what we want the first time we ever see the database:
    otherwise every pre-existing score would appear as if it had just
    been set.
    """
    now = datetime.now(timezone.utc)
    seen = {(s["user"], s["hash"], s["diff"]): s["points"]
            for s in db.hs_snapshot.find({}, {"_id": 0})}

    events, updates = [], []
    for doc in db.scores.find({}, {"_id": 0, "hash": 1, "username": 1, "score": 1}):
        for diff, entry in decode(doc.get("score", "")).items():
            key = (doc["username"], doc["hash"], diff)
            if seen.get(key) == entry["points"]:
                continue
            if emit:
                events.append({
                    "ts": now, "user": doc["username"], "hash": doc["hash"],
                    "diff": diff, "previous": seen.get(key),
                    **{k: entry[k] for k in SCORE_KEYS},
                    "crown": entry["crown"], "accuracy": entry["accuracy"],
                })
            updates.append({"user": doc["username"], "hash": doc["hash"],
                            "diff": diff, "points": entry["points"]})

    if events:
        db.hs_events.insert_many(events)
    for u in updates:
        db.hs_snapshot.replace_one(
            {"user": u["user"], "hash": u["hash"], "diff": u["diff"]}, u, upsert=True)
    return len(updates)


def bootstrap():
    """Seed the snapshot on first ever run, silently."""
    if db.hs_snapshot.count_documents({}, limit=1) == 0:
        n = poll_once(emit=False)
        print(f"bootstrap: seeded {n} existing scores without events", flush=True)


def start_poller():
    bootstrap()

    def loop():
        while True:
            try:
                poll_once()
            except Exception as exc:
                print("poll failed:", exc, flush=True)
            time.sleep(POLL_SECONDS)

    threading.Thread(target=loop, daemon=True).start()


def recent_events(limit=40):
    """Real events if we have them; otherwise synthesise a feed from the
    current standings so a fresh install isn't blank."""
    snap = snapshot()
    out = []
    for e in db.hs_events.find().sort("ts", -1).limit(limit):
        song = snap["songs"].get(e["hash"])
        if not song:
            continue
        board = snap["boards"].get((e["hash"], e["diff"]), [])
        rank = next((r["rank"] for r in board if r["user"] == e["user"]), None)
        out.append({**e, "song": song, "rank": rank,
                    "players": len(board), "historic": False})

    if len(out) >= limit:
        return out

    have = {(e["user"], e["hash"], e["diff"]) for e in out}
    fallback = []
    for (h, diff), board in snap["boards"].items():
        song = snap["songs"].get(h)
        if not song:
            continue
        for r in board:
            if (r["user"], h, diff) in have:
                continue
            fallback.append({**r, "hash": h, "diff": diff, "song": song,
                             "players": len(board), "ts": None, "historic": True})
    fallback.sort(key=lambda r: r["points"], reverse=True)
    return out + fallback[: limit - len(out)]


# ---------------------------------------------------------------- snapshot

_cache = {"at": 0.0, "data": None}
_lock = threading.Lock()


def snapshot():
    with _lock:
        if _cache["data"] and time.time() - _cache["at"] < CACHE_SECONDS:
            return _cache["data"]
        data = _build()
        _cache.update(at=time.time(), data=data)
        return data


def _build():
    songs = {}
    for s in db.songs.find({"hash": {"$ne": None}},
                           {"_id": 0, "hash": 1, "id": 1, "title": 1,
                            "subtitle": 1, "category_id": 1, "courses": 1}):
        songs[s["hash"]] = s

    cats = {c["id"]: c for c in
            db.categories.find({}, {"_id": 0, "id": 1, "title": 1, "song_skin": 1})}

    # boards[(hash, diff)] = [entry, ...] ranked
    boards = defaultdict(list)
    for doc in db.scores.find({}, {"_id": 0, "hash": 1, "username": 1, "score": 1}):
        if doc["hash"] not in songs:
            continue
        for diff, entry in decode(doc.get("score", "")).items():
            boards[(doc["hash"], diff)].append({"user": doc["username"], **entry})

    for key, rows in boards.items():
        rows.sort(key=lambda r: r["points"], reverse=True)
        for i, r in enumerate(rows):
            r["rank"] = i + 1

    # per-difficulty pool of songs anyone has played
    pools = defaultdict(set)
    for (h, diff) in boards:
        pools[diff].add(h)

    users = defaultdict(lambda: {
        "name": "", "plays": 0, "firsts": 0,
        "crowns": {"silver": 0, "gold": 0, "rainbow": 0},
        "per_diff": defaultdict(lambda: {"plays": 0, "firsts": 0, "rank_sum": 0,
                                         "crowns": {"silver": 0, "gold": 0, "rainbow": 0}}),
        "genres": defaultdict(int),
    })

    for (h, diff), rows in boards.items():
        song = songs[h]
        for r in rows:
            u = users[r["user"]]
            u["name"] = r["user"]
            u["plays"] += 1
            d = u["per_diff"][diff]
            d["plays"] += 1
            d["rank_sum"] += r["rank"]
            if r["rank"] == 1:
                u["firsts"] += 1
                d["firsts"] += 1
            if r["crown"]:
                u["crowns"][r["crown"]] += 1
                d["crowns"][r["crown"]] += 1
            if song.get("category_id"):
                u["genres"][song["category_id"]] += 1

    # average placement over the whole pool, unplayed counting as last+1
    for name, u in users.items():
        for diff, pool in pools.items():
            d = u["per_diff"][diff]
            missing = len(pool) - d["plays"]
            penalty = sum(len(boards[(h, diff)]) + 1
                          for h in pool
                          if not any(r["user"] == name for r in boards[(h, diff)]))
            total = d["rank_sum"] + penalty
            count = d["plays"] + missing
            d["avg_rank"] = total / count if count else 0
            d["pool"] = len(pool)
            d["coverage"] = d["plays"] / len(pool) * 100 if pool else 0

    return {"songs": songs, "cats": cats, "boards": boards,
            "pools": pools, "users": users}


def records(limit=20):
    """Events that took first place, newest first."""
    snap = snapshot()
    out = []
    for e in db.hs_events.find().sort("ts", -1).limit(400):
        song = snap["songs"].get(e["hash"])
        if not song:
            continue
        board = snap["boards"].get((e["hash"], e["diff"]), [])
        if board and board[0]["user"] == e["user"] and board[0]["points"] == e["points"]:
            out.append({**e, "song": song,
                        "previous_holder": board[1]["user"] if len(board) > 1 else None,
                        "previous_points": board[1]["points"] if len(board) > 1 else None})
        if len(out) >= limit:
            break
    return out
