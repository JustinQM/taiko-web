"""The animation shown when a song finishes.

There is a seven second gap between the music fading out and the results
screen appearing, and nothing was drawn in it -- the clear and fail
sounds were already playing into silence.

These drive the drawing against a recording context, since it is a canvas
routine with nothing else to observe.
"""

import pytest

DRIVE = """
(args) => {
    const view = Object.create(View.prototype)
    const drawn = []
    const ctx = {
        globalAlpha: 1, globalCompositeOperation: "source-over",
        save(){}, restore(){}, translate(){}, scale(){}, rotate(){},
        drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh){
            drawn.push({name: current, x: dx + dw / 2, y: dy + dh / 2, w: dw})
        },
    }
    // Names are resolved through assets.image; record which are asked for.
    const asked = []
    let current = null
    const realSheet = View.prototype.endingSheet
    view.endingSheet = function(name, ...rest){
        asked.push(name)
        current = name
        return realSheet.call(this, name, ...rest)
    }
    view.player = args.second ? 2 : 1
    // Everything lines up with the play line rather than with fixed
    // screen coordinates, so the driver has to supply one.
    view.slotPos = {x: 413, y: args.second ? 617 : 257, size: 106, paddingLeft: 332}
    view.rules = {clearReached: () => args.cleared}
    // A real song is well into its elapsed time by the time it ends;
    // zero would read as "the fade has not started".
    const started = 120000
    view.controller = {
        game: {fadeOutStarted: started, elapsedTime: started + 1600 + args.elapsed},
        getGlobalScore: () => ({gauge: 100, bad: args.bad, ok: 0}),
    }
    view.drawEndingAnimation(ctx, 1280, 720)
    // How far apart the two sticks are, and where things are centered.
    const sticks = drawn.filter(d => /bachio_[lr]_(in|out)/.test(d.name || ""))
    const spread = sticks.length > 1
        ? Math.max(...sticks.map(s => s.x)) - Math.min(...sticks.map(s => s.x)) : 0
    // Positions, not widths: the public build draws 1x1 placeholders, so
    // only where things are put is real there.
    const pieces = drawn.filter(d => /clear_separated$/.test(d.name || ""))
        .map(d => d.x).sort((a, b) => a - b)
    const gaps = pieces.slice(1).map((x, i) => Math.round((x - pieces[i]) * 10) / 10)
    const centerX = (view.slotPos.paddingLeft + 1280) / 2
    return {
        asked: [...new Set(asked)],
        drew: drawn.length,
        spread: spread,
        pieceGaps: gaps,
        pieceSpan: pieces.length ? pieces[pieces.length - 1] - pieces[0] : 0,
        stickOffset: sticks.length
            ? Math.min(...sticks.map(s => Math.abs(s.x - centerX))) : 0,
        centers: {y: view.slotPos.y},
    }
}
"""


@pytest.fixture
def drive(game):
    def run(elapsed, cleared=True, bad=0, second=False):
        return game.page.evaluate(DRIVE, {
            "elapsed": elapsed, "cleared": cleared, "bad": bad, "second": second})
    return run


def test_nothing_before_the_music_has_faded(drive):
    assert drive(-200)["asked"] == []


def test_nothing_after_the_results_screen(drive):
    assert drive(8000)["asked"] == []


def test_the_sticks_fly_in_first(drive):
    asked = drive(100)["asked"]
    assert "yatai_ending_bachio_l_in" in asked
    assert "yatai_ending_bachio_r_in" in asked


def test_only_a_full_combo_gets_fans(drive):
    """The skin's clear animation draws no fans at all; they belong to the
    full combo one, and start after its panel has bounced."""
    assert "yatai_ending_fan_l" not in drive(1000, cleared=True, bad=3)["asked"]
    assert "yatai_ending_fan_l" not in drive(200, cleared=True, bad=0)["asked"]
    assert "yatai_ending_fan_l" in drive(1000, cleared=True, bad=0)["asked"]


def test_a_clear_assembles_out_of_five_pieces(drive):
    """The skin splits the word up and fades the pieces in one after
    another rather than showing it whole."""
    asked = drive(600, cleared=True, bad=3)["asked"]
    assert "yatai_ending_clear_separated" in asked
    assert "yatai_ending_full_combo" not in asked
    assert "yatai_ending_fail" not in asked


def test_a_full_combo_shows_its_own_panel_and_confetti(drive):
    asked = drive(1000, cleared=True, bad=0)["asked"]
    assert "yatai_ending_full_combo" in asked
    assert "yatai_ending_confetti" in asked


def test_a_clear_gets_no_confetti(drive):
    assert "yatai_ending_confetti" not in drive(1000, cleared=True, bad=3)["asked"]


def test_the_word_pieces_use_the_skin_spacing(game, drive):
    """They are spaced by the skin's 60, not by their own 80px width.

    Spacing them at their width stretched the word a quarter wider than it
    should be, which is what pushed it out under the drumsticks. Measured
    from where the pieces are placed rather than how wide they are drawn,
    because the public build's art is all 1x1 placeholders.
    """
    gaps = drive(500, cleared=True, bad=3)["pieceGaps"]
    spacing = game.page.evaluate("() => View.ENDING.pieceSpacing")
    assert spacing == 60
    assert gaps and all(g == pytest.approx(spacing) for g in gaps), \
        f"pieces are {gaps} apart, expected {spacing}"


def test_the_sticks_end_up_outside_the_word(drive):
    """They are drawn over the panel, so they have to finish beside it."""
    result = drive(2000, cleared=True, bad=3)
    half_word = max(result["pieceSpan"] / 2, 1)
    assert result["stickOffset"] > half_word, \
        f"sticks sit {result['stickOffset']} from center, inside a word half-width of {half_word}"


def test_a_fail_shows_the_fail_panel(drive):
    asked = drive(600, cleared=False, bad=40)["asked"]
    assert "yatai_ending_fail" in asked
    assert "yatai_ending_confetti" not in asked


def test_the_panel_waits_for_the_sticks(drive):
    assert "yatai_ending_clear_separated" not in drive(100, cleared=True, bad=3)["asked"]
    assert "yatai_ending_clear_separated" in drive(600, cleared=True, bad=3)["asked"]


def test_the_panel_pieces_arrive_one_after_another(drive):
    """Each fades in over 100ms, 50ms behind the last."""
    early = drive(200, cleared=True, bad=3)["drew"]
    late = drive(500, cleared=True, bad=3)["drew"]
    assert late > early, f"all pieces appeared at once: {early} then {late}"


def test_the_sticks_leave_after_landing(drive):
    assert "yatai_ending_bachio_l_out" in drive(500)["asked"]
    assert "yatai_ending_bachio_l_in" not in drive(500)["asked"]


def test_the_sticks_stay_once_they_have_swept_apart(drive):
    """The skin keeps drawing the last out-frame until the results screen,
    rather than the sticks vanishing mid-animation."""
    asked = drive(3000)["asked"]
    assert "yatai_ending_bachio_l_out" in asked
    assert "yatai_ending_bachio_l_in" not in asked


def test_the_sticks_sweep_apart(game, drive):
    """Without this they only blinked between frames, which read as a
    flicker rather than a movement. They start 58px apart rather than on
    top of each other, so they look like two sticks separating."""
    rest = game.page.evaluate("() => View.ENDING.stickRest * 2")
    spread = drive(0)["spread"], drive(150)["spread"], drive(400)["spread"]
    assert spread[0] == pytest.approx(rest), f"they did not start at rest: {spread[0]}"
    assert spread[1] == pytest.approx(rest), "the sweep started early"
    assert spread[2] > spread[1] + 300, f"they barely moved: {spread}"


def test_everything_lines_up_with_the_play_line(drive):
    """The skin's coordinates are for a fixed stage; this canvas is
    whatever the window is, so the play line is the anchor."""
    centers = drive(600)["centers"]
    assert centers["y"] == 257, f"drawn off the play line: {centers}"


def test_it_draws_for_the_second_player_too(drive):
    """The sheet is laid out with a 1P and a 2P position for everything."""
    assert drive(600, second=True)["drew"] > 0


def test_frames_stay_inside_their_sheets(drive):
    """A frame index past the end reads whatever follows it in the strip."""
    for elapsed in (0, 100, 200, 300, 420, 500, 600, 900, 1500, 3000, 6900):
        result = drive(elapsed)
        assert result["drew"] >= 0
    assert drive(6999)["asked"] != []
