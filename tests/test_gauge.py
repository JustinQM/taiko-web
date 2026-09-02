"""The rainbow gauge overlay, in one and two player.

drawGaugeRainbow drew the overlay at the same place for both players --
the vertical offset was even written as a ternary whose two arms were
identical -- while gauge() draws the second player's gauge mirrored about
its midline. The overlay therefore lay over the wrong half of it.

These drive the real method against a recording context, because the
overlay is one drawImage inside a 1500-line canvas routine and there is
nothing else to assert on.
"""

import pytest

# Records the transform and the destination rectangle of each drawImage.
SPY = """
(args) => {
    const draw = new CanvasDraw(false)
    const calls = []
    let m = {ty: 0, sy: 1}
    const ctx = {
        globalAlpha: 1,
        save(){}, restore(){},
        translate(x, y){ m = {ty: m.ty + y * m.sy, sy: m.sy} },
        scale(x, y){ m = {ty: m.ty, sy: m.sy * y} },
        drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh){
            // where the destination rectangle lands after the transform
            const top = m.ty + dy * m.sy
            const bottom = m.ty + (dy + dh) * m.sy
            calls.push({
                frameRow: sy / sh,
                top: Math.min(top, bottom),
                bottom: Math.max(top, bottom),
                flipped: m.sy < 0,
            })
        },
    }
    draw.drawGaugeRainbow(ctx, {
        ctx: ctx,
        percentage: 1,
        clear: 0.7,
        multiplayer: args.multiplayer,
        blue: args.multiplayer,
        scoresheet: false,
    })
    return calls
}
"""


@pytest.fixture
def spy(game):
    def run(multiplayer):
        return game.page.evaluate(SPY, {"multiplayer": multiplayer})
    return run


def test_overlay_is_drawn_for_both_players(spy):
    assert len(spy(False)) == 2, "one player: expected two blended frames"
    assert len(spy(True)) == 2, "two player: expected two blended frames"


def test_second_player_overlay_is_mirrored(spy):
    p1 = spy(False)[0]
    p2 = spy(True)[0]
    assert p1["flipped"] is False
    assert p2["flipped"] is True, "the second player's overlay is not mirrored"


def test_mirrored_overlay_covers_the_mirrored_gauge(spy):
    """gauge() puts the first player's bar at y 30..52 and the second
    player's at 0..22, a flip about y = 52. The overlay has to follow."""
    p1 = spy(False)[0]
    p2 = spy(True)[0]
    assert p1["top"] == pytest.approx(-8), p1
    assert p1["bottom"] == pytest.approx(56), p1
    assert p2["top"] == pytest.approx(52 - 56), p2
    assert p2["bottom"] == pytest.approx(52 + 8), p2


def test_overlay_only_appears_on_a_full_gauge(game):
    calls = game.page.evaluate("""() => {
        const draw = new CanvasDraw(false)
        const calls = []
        const ctx = {globalAlpha: 1, save(){}, restore(){}, translate(){}, scale(){},
                     drawImage(){ calls.push(1) }}
        draw.drawGaugeRainbow(ctx, {ctx: ctx, percentage: 0.5, clear: 0.7,
                                    multiplayer: false, blue: false, scoresheet: false})
        return calls.length
    }""")
    assert calls == 0, "the overlay was drawn on a gauge that is not full"
