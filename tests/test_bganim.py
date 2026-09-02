"""The animation primitives the background is built out of.

They are a port of YataiDON's, and the skin's numbers only mean anything
against their exact semantics: a delay that holds the starting value
rather than zero, an easing that applies to the progress rather than the
value, a reverse that happens once and then finishes, and a loop that
restarts on the frame after it ended.

The numbers here are the test's own. What is being checked is the shape.
"""

import pytest


@pytest.fixture
def anim(game):
    """A page with the classes loaded and the clock at a known place."""
    game.page.evaluate("() => { BgAnim.now = 0 }")
    return game.page


def move(page, opts, at):
    """Build a move, run it to each timestamp, and report the attribute."""
    return page.evaluate("""([opts, at]) => {
        BgAnim.now = 0
        const anim = new BgMove(opts.duration, opts)
        anim.start()
        return at.map(ms => { anim.update(ms); return anim.attribute })
    }""", [opts, at])


def test_a_delay_holds_the_starting_value(anim):
    """Not zero -- a move that starts off-screen waits off-screen."""
    values = move(anim, {"duration": 100, "total_distance": 50,
                         "start_position": -200, "delay": 500}, [0, 250, 499])
    assert values == [-200, -200, -200]


def test_a_move_is_linear_without_easing(anim):
    values = move(anim, {"duration": 100, "total_distance": 100}, [25, 50, 75])
    assert values == [25, 50, 75]


def test_ease_out_covers_most_of_the_distance_early(anim):
    """progress * (2 - progress): three quarters of the way at half time."""
    values = move(anim, {"duration": 100, "total_distance": 100,
                         "ease_out": "quadratic"}, [50])
    assert values[0] == pytest.approx(75)


def test_ease_in_covers_least(anim):
    values = move(anim, {"duration": 100, "total_distance": 100,
                         "ease_in": "quadratic"}, [50])
    assert values[0] == pytest.approx(25)


def test_ease_in_wins_when_both_are_given(anim):
    """Several of the skin's animations declare both, and the original
    checks ease_in first."""
    values = move(anim, {"duration": 100, "total_distance": 100,
                         "ease_in": "quadratic", "ease_out": "quadratic"}, [50])
    assert values[0] == pytest.approx(25)


def test_a_move_finishes_at_the_end(anim):
    finished = anim.evaluate("""() => {
        BgAnim.now = 0
        const anim = new BgMove(100, {total_distance: 10})
        anim.start()
        anim.update(99)
        const before = anim.isFinished
        anim.update(100)
        return [before, anim.isFinished, anim.attribute]
    }""")
    assert finished == [False, True, 10]


def test_reverse_delay_turns_a_move_into_a_there_and_back(anim):
    """It happens once: out, back, then finished. A loop on top of it is
    what makes the skin's bobbing overlays bob forever."""
    result = anim.evaluate("""() => {
        BgAnim.now = 0
        const anim = new BgMove(100, {total_distance: 20, reverse_delay: 0})
        anim.start()
        const seen = []
        anim.update(100); seen.push([anim.attribute, anim.isFinished])
        anim.update(150); seen.push([anim.attribute, anim.isFinished])
        anim.update(200); seen.push([anim.attribute, anim.isFinished])
        return seen
    }""")
    assert result[0] == [20, False], "it should turn around rather than finish"
    assert result[1] == [10, False], "it should be halfway back"
    assert result[2] == [0, True], "it should finish where it started"


def test_a_loop_restarts_rather_than_finishing(anim):
    result = anim.evaluate("""() => {
        BgAnim.now = 0
        const anim = new BgMove(100, {total_distance: 10, loop: true})
        anim.update(100)
        const ended = anim.isFinished
        BgAnim.now = 100
        anim.update(100)
        return [ended, anim.isFinished, anim.attribute]
    }""")
    assert result == [True, False, 0]


def test_a_loop_needs_no_start(anim):
    """The original marks a looping animation as started when it is made,
    which is why the skin never starts one."""
    started = anim.evaluate(
        "() => new BgMove(100, {total_distance: 1, loop: true}).isStarted")
    assert started is True


def test_a_fade_interpolates_between_its_two_opacities(anim):
    values = anim.evaluate("""() => {
        BgAnim.now = 0
        const anim = new BgFade(100, {initial_opacity: 0.5, final_opacity: 0.4})
        anim.start()
        return [25, 50, 100].map(ms => { anim.update(ms); return anim.attribute })
    }""")
    assert values[0] == pytest.approx(0.475)
    assert values[1] == pytest.approx(0.45)
    assert values[2] == pytest.approx(0.4)


def test_a_fade_reverses_by_swapping_its_ends(anim):
    values = anim.evaluate("""() => {
        BgAnim.now = 0
        const anim = new BgFade(100, {initial_opacity: 0, final_opacity: 1, reverse_delay: 0})
        anim.start()
        anim.update(100)
        const out = [anim.attribute]
        anim.update(150)
        out.push(anim.attribute)
        anim.update(200)
        out.push(anim.attribute)
        return out
    }""")
    assert values == [1, pytest.approx(0.5), 0]


def test_a_texture_change_holds_each_frame_for_its_span(anim):
    frames = anim.evaluate("""() => {
        BgAnim.now = 0
        const anim = BgTextureChange.even(300, 3, {})
        anim.start()
        return [50, 150, 250].map(ms => { anim.update(ms); return anim.attribute })
    }""")
    assert frames == [0, 1, 2]


def test_a_texture_change_finishes_unless_it_loops(anim):
    result = anim.evaluate("""() => {
        BgAnim.now = 0
        const once = BgTextureChange.even(300, 3, {})
        once.start()
        once.update(400)
        BgAnim.now = 0
        const looping = BgTextureChange.even(300, 3, {loop: true})
        looping.update(400)
        BgAnim.now = 400
        looping.update(400)
        looping.update(450)
        return [once.isFinished, looping.isFinished, looping.attribute]
    }""")
    assert result == [True, False, 0]
