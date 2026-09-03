#!/usr/bin/env python3
"""Measure how long the game spends on each frame.

Not a test: an instrument. "It feels smoother" is not a result, and the
existing tests cannot see frame timing at all. This drives a real browser
against the private stack -- the one with real assets and playable songs,
because the public one has neither and would measure something that does
not exist -- and records every frame from inside the page.

    tests/perf/framecheck.py --label before
    ...make a change...
    tests/perf/framecheck.py --label after --compare before

Runs are written to tests/perf/results/<label>.json so two builds can be
put side by side. The numbers that matter are not the average: a rhythm
game is judged on its worst frames, because those are the ones that cost
notes.
"""

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get("TAIKO_URL", "http://localhost:34900")
RESULTS = Path(__file__).parent / "results"

# Recorded from inside the page: requestAnimationFrame deltas, tagged with
# whichever scene is on screen, so gameplay can be told apart from menus.
RECORDER = """
(stallMs) => {
    window.__frames = []
    window.__draws = []
    window.__scene = "boot"
    let last = performance.now()
    const tick = now => {
        window.__frames.push([window.__scene, now - last])
        last = now
        window.__raf = requestAnimationFrame(tick)
    }
    window.__raf = requestAnimationFrame(tick)

    // Frame deltas are pinned to the display's 16.7ms whenever the game
    // is keeping up, so they show dropped frames but say nothing about
    // how much room is left before it stops keeping up. Timing the game's
    // own draw is what shows headroom, and it is what the performance
    // work is actually trying to move.
    const wrap = (proto, name, tag) => {
        if (!proto || typeof proto[name] !== "function") return
        const real = proto[name]
        proto[name] = function(...args) {
            const t0 = performance.now()
            try { return real.apply(this, args) }
            finally {
                if (stallMs) {
                    const until = performance.now() + stallMs
                    while (performance.now() < until) {}
                }
                window.__draws.push([tag, performance.now() - t0])
            }
        }
    }
    wrap(typeof View !== "undefined" && View.prototype, "refresh", "gameplay")
    wrap(typeof SongSelect !== "undefined" && SongSelect.prototype, "redraw", "songselect")
}
"""


def percentile(values, p):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def summarize(frames):
    """Per scene, the shape of the distribution and the frames that hurt."""
    scenes = {}
    for scene, ms in frames:
        scenes.setdefault(scene, []).append(ms)

    out = {}
    for scene, times in scenes.items():
        # The first frame of a scene includes whatever set it up, which is
        # a loading cost rather than a drawing one.
        times = times[1:] or times
        out[scene] = {
            "frames": len(times),
            "median": round(statistics.median(times), 2),
            "p95": round(percentile(times, 95), 2),
            "p99": round(percentile(times, 99), 2),
            "worst": round(max(times), 2),
            # A 60Hz frame is 16.7ms and jitters either side of it, so
            # counting "over 16.7" counts noise. Over 20 is a frame that
            # was actually missed; over 33 is two.
            "dropped": sum(1 for t in times if t > 20),
            "dropped2": sum(1 for t in times if t > 33),
        }
    return out


def run(song_index, seconds, stall_ms=0):
    with sync_playwright() as p:
        browser = p.chromium.launch(args=[
            "--autoplay-policy=no-user-gesture-required",
            # Without this Chromium may pick a software path that is not
            # what anyone actually plays on.
            "--enable-gpu-rasterization",
        ])
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(URL, wait_until="networkidle", timeout=120000)
        page.wait_for_function(
            "() => typeof SongSelect !== 'undefined' && assets.songs.length",
            timeout=60000)

        page.evaluate(RECORDER, stall_ms)
        page.evaluate("""() => {
            try { localStorage.setItem("tutorial", "true") } catch(e) {}
            window.__ss = new SongSelect(false, false, false)
            window.__scene = "songselect"
        }""")
        page.wait_for_timeout(1500)

        # Move through the wheel, which is what song select actually does.
        for _ in range(12):
            page.evaluate("() => __ss.moveToSong(1)")
            page.wait_for_timeout(180)

        # Into a folder and onto a real song, then through the game's own
        # path rather than reconstructing the call it makes: shift means
        # autoplay, so this plays itself.
        started = page.evaluate("""(index) => {
            const songs = __ss.navigator.songItems
            const song = songs[index % songs.length]
            const t = __ss.navigator.locate(song)
            __ss.enterListing(__ss.navigator.jumpToPath(t.path, t.index))
            const chosen = __ss.songs[__ss.selectedSong]
            if (!chosen || !chosen.courses) return null
            const diff = ["oni", "hard", "normal", "easy"].find(d => chosen.courses[d])
            window.__scene = "loading"
            __ss.selectedDiff = __ss.diffOptions.length + ["easy", "normal", "hard", "oni"].indexOf(diff)
            __ss.state.screen = "difficulty"
            __ss.toLoadSong(["easy", "normal", "hard", "oni"].indexOf(diff), true)
            return chosen.title + " (" + diff + ")"
        }""", song_index)
        if not started:
            browser.close()
            raise SystemExit("could not start a song")

        # The game canvas only exists once the song is actually playing.
        page.wait_for_selector("#canvas", timeout=180000)
        page.wait_for_timeout(2000)
        page.evaluate("() => { window.__scene = 'gameplay' }")
        page.wait_for_timeout(seconds * 1000)

        frames = page.evaluate("() => window.__frames")
        draws = page.evaluate("() => window.__draws")
        browser.close()
        return started, frames, draws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="name this run")
    ap.add_argument("--compare", help="a previous label to sit beside it")
    ap.add_argument("--song", type=int, default=100)
    ap.add_argument("--seconds", type=int, default=25)
    ap.add_argument("--stall", type=float, default=0,
                    help="inject this many ms into every draw, to check "
                         "the harness can actually see a regression")
    args = ap.parse_args()

    title, frames, draws = run(args.song, args.seconds, args.stall)
    result = {
        "label": args.label,
        "song": title,
        "scenes": summarize(frames),
        "draw": summarize(draws),
    }

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{args.label}.json").write_text(json.dumps(result, indent=1))

    previous = None
    if args.compare:
        path = RESULTS / f"{args.compare}.json"
        if path.exists():
            previous = json.loads(path.read_text())
        else:
            print(f"no previous run called {args.compare}", file=sys.stderr)

    print(f"\n{args.label}  ({title})")
    header = f"{'scene':<12}{'frames':>7}{'median':>9}{'p95':>8}{'p99':>8}{'worst':>8}{'drop':>7}{'drop2':>7}"
    print(header)
    print("-" * len(header))
    for scene, s in result["draw"].items():
        print(f"{'draw:' + scene:<12}{s['frames']:>7}{s['median']:>9}{s['p95']:>8}"
              f"{s['p99']:>8}{s['worst']:>8}{s['dropped']:>7}{s['dropped2']:>7}")
        if previous and scene in previous.get("draw", {}):
            was = previous["draw"][scene]
            print(f"{'was ' + args.compare:<12}{was['frames']:>7}{was['median']:>9}"
                  f"{was['p95']:>8}{was['p99']:>8}{was['worst']:>8}"
                  f"{was['dropped']:>7}{was['dropped2']:>7}")
    for scene, s in result["scenes"].items():
        print(f"{scene:<12}{s['frames']:>7}{s['median']:>9}{s['p95']:>8}"
              f"{s['p99']:>8}{s['worst']:>8}{s['dropped']:>7}{s['dropped2']:>7}")
        if previous and scene in previous["scenes"]:
            was = previous["scenes"][scene]
            delta = f"{'was ' + args.compare:<12}{was['frames']:>7}{was['median']:>9}" \
                    f"{was['p95']:>8}{was['p99']:>8}{was['worst']:>8}" \
                    f"{was['dropped']:>7}{was['dropped2']:>7}"
            print(delta)
    print()


if __name__ == "__main__":
    main()
