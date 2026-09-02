"""The rainbow soul flame.

Eight frames around the soul glyph while the gauge is full, cycled at the
same rate as the rainbow gauge overlay so the two read as one effect.
"""

import pytest

def spy(game, full):
    return game.page.evaluate("""(args) => {
        const draw = new CanvasDraw(false)
        draw.soulFireStart = {}
        const calls = []
        const ctx = {
            globalAlpha: 1, globalCompositeOperation: "source-over",
            save(){}, restore(){}, translate(){}, scale(){}, fill(){},
            fillStyle: "",
            drawImage(img, sx, sy, sw, sh){
                calls.push({row: sh ? sy / sh : 0, blend: ctx.globalCompositeOperation})
            },
        }
        const cfg = {ctx: ctx, x: 0, y: 0, cleared: true, full: args.full,
                     multiplayer: false}
        draw.soul(cfg)
        draw.soul(cfg)
        return calls
    }""", {"full": full})


def test_no_flame_until_the_gauge_is_full(game):
    assert spy(game, False) == []


def test_the_flame_draws_when_the_gauge_is_full(game):
    calls = spy(game, True)
    assert len(calls) >= 1, "nothing was drawn on a full gauge"


def test_it_is_drawn_additively(game):
    """It is a flame, so it adds light rather than covering the glyph."""
    calls = spy(game, True)
    assert all(c["blend"] == "lighter" for c in calls), \
        f"unexpected blend: {[c['blend'] for c in calls]}"


def test_it_cycles_through_its_frames(game):
    rows = game.page.evaluate("""() => {
        const draw = new CanvasDraw(false)
        draw.soulFireStart = {}
        const seen = new Set()
        const ctx = {
            globalAlpha: 1, globalCompositeOperation: "source-over",
            save(){}, restore(){}, translate(){}, scale(){}, fill(){}, fillStyle: "",
            drawImage(img, sx, sy, sw, sh){ seen.add(sh ? sy / sh : 0) },
        }
        const cfg = {ctx: ctx, x: 0, y: 0, cleared: true, full: true}
        // wind the clock by lying about when it started
        for (let f = 0; f < 8; f++) {
            draw.soulFireStart.p1 = performance.now() - f * 75 - 200
            draw.soul(cfg)
        }
        return [...seen].sort((a, b) => a - b)
    }""")
    assert len(rows) >= 4, f"only reached frames {rows}"
    assert max(rows) <= 7, f"read past the end of the strip: {rows}"
