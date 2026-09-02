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
            drawn.push({name: current, x: dx + dw / 2, y: dy + dh / 2})
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
    // How far apart the two sticks are, and where things are centred.
    const sticks = drawn.filter(d => /bachio_[lr]_(in|out)/.test(d.name || ""))
    const spread = sticks.length > 1
        ? Math.max(...sticks.map(s => s.x)) - Math.min(...sticks.map(s => s.x)) : 0
    return {
        asked: [...new Set(asked)],
        drew: drawn.length,
        spread: spread,
        centres: {y: view.slotPos.y},
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


def test_the_fans_sweep_at_the_start_and_stop(drive):
    assert "yatai_ending_fan_l" in drive(200)["asked"]
    assert "yatai_ending_fan_l" not in drive(1000)["asked"]


def test_a_clear_assembles_out_of_five_pieces(drive):
    """The skin splits the word up and fades the pieces in one after
    another rather than showing it whole."""
    asked = drive(600, cleared=True, bad=3)["asked"]
    assert "yatai_ending_clear_separated" in asked
    assert "yatai_ending_full_combo" not in asked
    assert "yatai_ending_fail" not in asked


def test_a_full_combo_shows_its_own_panel_and_confetti(drive):
    asked = drive(600, cleared=True, bad=0)["asked"]
    assert "yatai_ending_full_combo" in asked
    assert "yatai_ending_confetti" in asked


def test_a_clear_gets_no_confetti(drive):
    assert "yatai_ending_confetti" not in drive(600, cleared=True, bad=3)["asked"]


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


def test_the_sticks_sweep_apart_from_the_centre(drive):
    """Without this they only blinked between frames, which read as a
    flicker rather than a movement."""
    spread = drive(0)["spread"], drive(150)["spread"], drive(400)["spread"]
    assert spread[0] == pytest.approx(0), "they did not start together"
    assert spread[2] > 300, f"they barely moved: {spread}"
    assert spread[1] < spread[2], "the sweep runs backwards"


def test_everything_lines_up_with_the_play_line(drive):
    """The skin's coordinates are for a fixed stage; this canvas is
    whatever the window is, so the play line is the anchor."""
    centres = drive(600)["centres"]
    assert centres["y"] == 257, f"drawn off the play line: {centres}"


def test_it_draws_for_the_second_player_too(drive):
    """The sheet is laid out with a 1P and a 2P position for everything."""
    assert drive(600, second=True)["drew"] > 0


def test_frames_stay_inside_their_sheets(drive):
    """A frame index past the end reads whatever follows it in the strip."""
    for elapsed in (0, 100, 200, 300, 420, 500, 600, 900, 1500, 3000, 6900):
        result = drive(elapsed)
        assert result["drew"] >= 0
    assert drive(6999)["asked"] != []
