"""How the wheel moves.

The structure of song select is tested elsewhere; this is about the feel,
modelled on YataiDON: an ease-out slide that takes most of the step, input
that interrupts rather than being dropped, and held input that turns into
a jump.

None of this replaces sitting in front of it, but it does pin the
properties that make it feel the way it does, so a later change has to
break them deliberately.
"""

import pytest


@pytest.fixture
def wheel(game):
    """Inside a genre folder, which is where scrolling actually happens.

    The root is a dozen folders and menu entries; a few hundred songs is
    the case the motion is for, and it leaves room to move in both
    directions without wrapping and making deltas unreadable.
    """
    wheel = game.open_song_select()
    wheel.enter_folder()
    wheel.select_index(100)
    return wheel


def test_the_slide_takes_most_of_the_step(wheel):
    """It used to be a fifth of it, with the rest spent resizing a box.

    scroll is the window the wheel actually travels in; the remainder is
    the selected box shrinking before and growing after.
    """
    share = wheel.page.evaluate("""() => {
        const s = __ss.songSelecting
        const changeSpeed = s.speed
        const resize = changeSpeed * s.resize
        const scrollDelay = changeSpeed * s.scrollDelay
        const scroll = (changeSpeed - resize) - resize - scrollDelay * 2
        return scroll / changeSpeed
    }""")
    assert share > 0.5, f"the wheel only travels for {share:.0%} of a step"


def test_the_slide_decelerates(wheel):
    """Ease-out cubic: over halfway by the time a third of it has passed.

    A linear slide would be exactly a third of the way at that point,
    which is what it used to do.
    """
    curve = wheel.page.evaluate(
        "() => [0.25, 0.5, 0.75].map(t => 1 - Math.pow(1 - t, 3))")
    linear = [0.25, 0.5, 0.75]
    assert all(c > l for c, l in zip(curve, linear)), \
        f"the slide is not ahead of linear: {curve}"
    assert curve[1] > 0.8, f"halfway through, only {curve[1]:.0%} travelled"


def test_input_during_a_slide_is_not_dropped(wheel):
    """Mashing used to do nothing: moveToSong returned early while locked.

    The inputs are 80ms apart -- inside the 166ms slide, so each arrives
    while the wheel is still moving, but outside the 50ms skip window, so
    each stays a single step.
    """
    wheel.settle()
    start = wheel.wheel()["selected"]
    for _ in range(3):
        wheel.page.evaluate("() => __ss.moveToSong(1)")
        wheel.page.wait_for_timeout(80)
    wheel.settle()
    moved = wheel.wheel()["selected"] - start
    assert moved == 3, f"three inputs mid-slide advanced the wheel by {moved}"


def test_rapid_input_becomes_a_jump(wheel):
    """Two inputs inside the skip window: the second is a jump."""
    wheel.settle()
    start = wheel.wheel()["selected"]
    skip_by = wheel.page.evaluate("() => __ss.songSelecting.skipBy")
    wheel.page.evaluate("() => __ss.moveToSong(1)")
    wheel.page.wait_for_timeout(10)
    wheel.page.evaluate("() => __ss.moveToSong(1)")
    wheel.settle()
    moved = wheel.wheel()["selected"] - start
    assert moved == 1 + skip_by, \
        f"a step then a rapid step moved {moved}, expected {1 + skip_by}"


def test_a_jump_lands_immediately(wheel):
    """YataiDON snaps a skip rather than sliding ten boxes past.

    Compared against an ordinary ten-step move, which is still travelling
    at the same point.
    """
    def moved_after(js, wait):
        wheel.settle()
        start = wheel.wheel()["selected"]
        wheel.page.evaluate(js)
        wheel.page.wait_for_timeout(wait)
        return wheel.page.evaluate("() => __ss.selectedSong") - start

    snapped = moved_after(
        "() => { __ss.lastMoveAt = __ss.getMS(); __ss.moveToSong(1) }", 40)
    slid = moved_after("() => { __ss.lastMoveAt = 0; __ss.moveToSong(10) }", 40)

    assert snapped == 10, f"the jump had not landed after 40ms ({snapped})"
    assert slid == 0, \
        f"an ordinary ten-step move also landed instantly ({slid}); " \
        "this test no longer distinguishes snapping from sliding"


def test_a_lone_input_is_still_a_single_step(wheel):
    """The skip window must not swallow ordinary navigation."""
    wheel.settle()
    start = wheel.wheel()["selected"]
    wheel.page.evaluate("() => { __ss.lastMoveAt = 0; __ss.moveToSong(1) }")
    wheel.settle()
    moved = wheel.wheel()["selected"] - start
    assert moved == 1, f"a single input moved {moved}"
    assert wheel.errors == []
