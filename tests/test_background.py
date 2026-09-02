"""What the gameplay background does, without any art.

The art is private and the public stack has none, so these tests hand the
background a manifest of their own: the same shape the real one has, with
their own numbers and no images behind it. Nothing draws, which is the
point -- what is being tested is the state machine that decides what
would be drawn, and that is where the faults were.

The one that prompted this: the band above the lanes has two frames, the
plain one and the one lit up for a clear, and reading them as an
animation made it flash between them twice a second.
"""

import pytest

# A manifest with every layer the scripts reach for and nothing behind
# them. The animation numbers are the test's own; only id 1, the clear
# fade, is asserted on.
MANIFEST = """() => {
    const layer = frames => ({frames: frames, w: 100, h: 100,
                              pos: [{x: 0, y: 0, x2: 100, y2: 100}]})
    const assetList = {}
    // The band above the lanes: two frames, plain and lit.
    for (const half of [1, 2]) {
        for (const key of ["background", "overlay", "footer"]) {
            assetList["yatai_donbg_0_" + half + "_" + key] = layer(2)
        }
    }
    for (let i = 0; i < 5; i++) {
        for (const part of ["loop", "start"]) {
            assetList["yatai_dancer_dancer_0_" + i + "_" + part] = layer(4)
        }
    }
    assetList["yatai_bg_normal_bg_0_background"] = layer(1)
    assetList["yatai_bg_normal_bg_0_overlay"] = layer(1)
    assetList["yatai_bg_fever_bg_fever_0_background"] = layer(10)
    assetList["yatai_fever_fever_0_overlay_l"] = layer(1)
    assetList["yatai_fever_fever_0_overlay_r"] = layer(1)
    assetList["yatai_footer_0"] = layer(1)
    assetList["yatai_renda_renda_0"] = layer(6)
    assetList["yatai_chibi_chibi_0_0"] = layer(4)
    assetList["yatai_chibi_chibi_bad_0"] = layer(5)

    const animations = {}
    for (let id = 0; id <= 30; id++) {
        animations[id] = {type: "move", duration: 100, total_distance: 0}
    }
    // The clear fade, which is the one this file is really about.
    animations[1] = {type: "fade", duration: 150,
                     initial_opacity: 0, final_opacity: 1}

    assets.backgrounds = {
        donSets: [0], bgSets: [0], feverSets: [0], dancerSets: [0],
        footers: [0], rendaSets: [0], chibiSets: [0],
        animations: animations, assets: assetList
    }
}"""

# Records what would have been drawn. BgTex.draw gives up before touching
# a canvas when the image is missing, so the spy goes in front of it.
SPY = """() => {
    window.__drawn = []
    const real = BgTex.prototype.draw
    BgTex.prototype.draw = function(ctx, key, params){
        window.__drawn.push({tex: this.prefix, key: key, params: params || {}})
        return real.call(this, ctx, key, params)
    }
}"""

BUILD = """() => {
    window.__ctx = document.createElement("canvas").getContext("2d")
    window.__bg = new GameBackground({
        controller: {selectedSong: {title: "test song", hash: "test"}},
        player: 1,
        beatInterval: 500
    })
    window.__frame = (ms, gauge) => {
        __bg.update(ms, gauge)
        window.__drawn = []
        __bg.draw(__ctx, 0, 0)
        return window.__drawn
    }
}"""


@pytest.fixture
def background(game):
    page = game.page
    page.evaluate(MANIFEST)
    page.evaluate(SPY)
    page.evaluate(BUILD)
    return page


def gauge(progress, clear=False, rainbow=False):
    return {"progress": progress, "clear": clear, "rainbow": rainbow}


def band_frames(drawn):
    """Which frame of the band was asked for, in draw order."""
    return [d["params"].get("frame", 0) for d in drawn
            if d["key"] == "background" and "donbg" in d["tex"]]


def test_the_band_does_not_animate(background):
    """The fault as reported: it flashed yellow and red. Frame 0 is the
    band and frame 1 is the same band lit for a clear -- neither is a
    frame of an animation, and below the clear line only the first is
    ever drawn."""
    seen = set()
    for ms in range(0, 3000, 100):
        drawn = background.evaluate("([ms, g]) => __frame(ms, g)", [ms, gauge(0.2)])
        seen.update(band_frames(drawn))
    assert seen == {0}, f"the band drew frames {sorted(seen)} while not cleared"


def test_clearing_fades_the_lit_band_in_over_the_plain_one(background):
    """Both are drawn, the lit one on top at a rising opacity -- rather
    than one replacing the other, which would be a cut."""
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.2)])
    fades = []
    for ms in [0, 50, 100, 150, 400]:
        drawn = background.evaluate("([ms, g]) => __frame(ms, g)", [ms, gauge(0.9, clear=True)])
        lit = [d for d in drawn
               if d["key"] == "background" and "donbg" in d["tex"]
               and d["params"].get("frame") == 1]
        assert len(lit) > 0, f"the lit band was not drawn at {ms}ms"
        fades.append(lit[0]["params"]["fade"])
    assert fades[0] == 0
    assert 0 < fades[1] < 1, f"it should be part way in at 50ms, got {fades[1]}"
    assert fades[2] > fades[1], "it should still be rising at 100ms"
    assert fades[3] == 1 and fades[4] == 1, "it should arrive and stay"


def test_dropping_below_the_clear_line_puts_the_band_back(background):
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.9, clear=True)])
    background.evaluate("([ms, g]) => __frame(ms, g)", [400, gauge(0.9, clear=True)])
    drawn = background.evaluate("([ms, g]) => __frame(ms, g)", [500, gauge(0.5)])
    assert band_frames(drawn) and set(band_frames(drawn)) == {0}


def test_a_song_starts_with_one_dancer(background):
    """Not five. The rest are earned."""
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0)])
    assert background.evaluate("() => __bg.dancers.activeCount") == 1


def test_dancers_arrive_as_the_gauge_fills(background):
    counts = []
    ms = 0
    for progress in [0, 0.2, 0.4, 0.6, 0.99]:
        ms += 100
        background.evaluate("([ms, g]) => __frame(ms, g)", [ms, gauge(progress)])
        counts.append(background.evaluate("() => __bg.dancers.activeCount"))
    assert counts == [1, 2, 3, 4, 5], counts


def test_the_fifth_dancer_only_arrives_on_a_clear(background):
    """Below the line the count is capped at four of the five marks, so
    a full house means the song is being cleared."""
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.79)])
    background.evaluate("([ms, g]) => __frame(ms, g)", [100, gauge(0.79)])
    below = background.evaluate("() => __bg.dancers.activeCount")
    assert below < 5, "a full house before the clear line"
    background.evaluate("([ms, g]) => __frame(ms, g)", [200, gauge(0.85, clear=True)])
    assert background.evaluate("() => __bg.dancers.activeCount") == 5


def test_dancers_leave_when_the_gauge_drops(background):
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.99)])
    background.evaluate("([ms, g]) => __frame(ms, g)", [100, gauge(0.99)])
    full = background.evaluate("() => __bg.dancers.activeCount")
    background.evaluate("([ms, g]) => __frame(ms, g)", [200, gauge(0.1)])
    assert background.evaluate("() => __bg.dancers.activeCount") < full


def test_dancers_fill_their_slots_from_the_middle_outwards(background):
    """Centre, then left, then right, and each keeps its place -- so an
    arrival does not shuffle the row sideways."""
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0)])
    background.evaluate("([ms, g]) => __frame(ms, g)", [100, gauge(0.2)])
    background.evaluate("([ms, g]) => __frame(ms, g)", [200, gauge(0.4)])
    filled = background.evaluate("() => __bg.dancers.activeDancers.map(d => !!d)")
    assert filled == [False, True, True, True, False], filled


def test_the_standard_scene_keeps_drawing_until_fever_has_arrived(background):
    """Otherwise the screen cuts from one to the other."""
    drawn = background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.9, clear=True)])
    prefixes = {d["tex"] for d in drawn}
    assert any("bg_normal" in p for p in prefixes)
    assert any("bg_fever" in p for p in prefixes)


def test_the_rainbow_overlay_only_appears_on_a_full_gauge(background):
    without = background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.9, clear=True)])
    with_it = background.evaluate("([ms, g]) => __frame(ms, g)",
                                  [100, gauge(1, clear=True, rainbow=True)])
    assert not any("_fever_fever_" in d["tex"] for d in without)
    assert any("_fever_fever_" in d["tex"] for d in with_it)


def test_a_song_gets_the_same_background_every_time(background):
    """It has to: the loader picks what to fetch before any of this
    exists, and two players in a session must see the same thing."""
    same = background.evaluate("""() => {
        const song = {title: "a song", hash: "abc"}
        const a = GameBackground.choose(song, assets.backgrounds)
        const b = GameBackground.choose(song, assets.backgrounds)
        return JSON.stringify(a) === JSON.stringify(b)
    }""")
    assert same is True


def test_the_loader_is_asked_for_what_the_background_will_draw(background):
    """The two used to be able to disagree, which loaded one background
    and drew another."""
    missing = background.evaluate("""() => {
        const song = {title: "a song", hash: "abc"}
        const wanted = GameBackground.assetsFor(song, assets.backgrounds)
        return Object.keys(assets.backgrounds.assets).filter(n => !wanted.includes(n))
    }""")
    assert missing == [], f"the background can draw layers nobody loads: {missing}"


def test_hits_and_misses_put_characters_on_the_screen(background):
    """And they are dropped once they have crossed, rather than piling up
    for the length of the song."""
    background.evaluate("([ms, g]) => __frame(ms, g)", [0, gauge(0.2)])
    counts = background.evaluate("""() => {
        __bg.handleHit()
        __bg.handleMiss()
        __bg.handleRoll()
        const after = [__bg.chibi.chibis.length, __bg.renda.rendas.length]
        // Long enough for both to have crossed the screen.
        BgAnim.now = 60000
        __bg.update(60000, {progress: 0.2, clear: false, rainbow: false})
        return after.concat([__bg.chibi.chibis.length, __bg.renda.rendas.length])
    }""")
    assert counts[0] == 2 and counts[1] == 1
    assert counts[2] == 0 and counts[3] == 0, "they were never dropped"
