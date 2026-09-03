"""How the wheel moves.

The structure of song select is tested elsewhere; this is about the feel,
modeled on YataiDON: an ease-out slide that takes most of the step, input
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


def test_the_wheel_travels_for_the_whole_step(wheel):
    """It used to travel for a fifth of it, spending the rest resizing a
    box, which is what made it read as snapping between positions."""
    curve = wheel.page.evaluate(
        "() => [0, 0.5, 0.99, 1].map(f => __ss.slideOffset(f * __ss.songSelecting.speed))")
    assert curve[0] == 1, "the wheel does not start a whole box behind"
    assert curve[3] == 0, "the wheel has not arrived at the end of the step"
    assert 0 < curve[2] < 0.01, f"it stopped early: {curve[2]} left at 99%"


def test_the_slide_decelerates(wheel):
    """Ease-out: most of the distance is covered early and it settles.

    Driven through the real function rather than recomputed here, because
    an earlier version of this test recomputed the curve and passed while
    the wheel was still sliding linearly.
    """
    remaining = wheel.page.evaluate(
        "() => [0.25, 0.5, 0.75].map(f => __ss.slideOffset(f * __ss.songSelecting.speed))")
    traveled = [1 - r for r in remaining]
    assert all(t > f for t, f in zip(traveled, [0.25, 0.5, 0.75])), \
        f"the slide is not ahead of linear: {traveled}"
    assert traveled[1] > 0.8, f"halfway through, only {traveled[1]:.0%} traveled"


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

    Compared against an ordinary ten-step move, which is still traveling
    at the same point.
    """
    def moved_after(js, wait):
        wheel.settle()
        start = wheel.wheel()["selected"]
        wheel.page.evaluate(js)
        wheel.page.wait_for_timeout(wait)
        return wheel.page.evaluate("() => __ss.selectedSong") - start

    snapped = wheel.page.evaluate("""() => {
        __ss.lastMoveAt = __ss.getMS()
        __ss.moveToSong(1)
        return {slide: __ss.state.slide, locked: __ss.state.locked}
    }""")
    wheel.settle()
    stepped = wheel.page.evaluate("""() => {
        __ss.lastMoveAt = 0
        __ss.moveToSong(1)
        return {slide: __ss.state.slide, locked: __ss.state.locked}
    }""")
    wheel.settle()

    assert snapped["slide"] == 0, "the jump is sliding rather than landing"
    assert snapped["locked"] == 0
    assert stepped["slide"] == 1, "an ordinary step should slide"


def test_a_lone_input_is_still_a_single_step(wheel):
    """The skip window must not swallow ordinary navigation."""
    wheel.settle()
    start = wheel.wheel()["selected"]
    wheel.page.evaluate("() => { __ss.lastMoveAt = 0; __ss.moveToSong(1) }")
    wheel.settle()
    moved = wheel.wheel()["selected"] - start
    assert moved == 1, f"a single input moved {moved}"
    assert wheel.errors == []


def test_holding_a_direction_does_not_jump(wheel):
    """A held key repeats at around 30ms, which is not the same gesture as
    pressing twice quickly. Treating it as one turned a held arrow into
    ten songs per repeat."""
    wheel.settle()
    start = wheel.wheel()["selected"]
    moved = wheel.page.evaluate("""() => {
        const from = __ss.selectedSong
        // three auto-repeats in the time one deliberate double-tap fits
        for (let i = 0; i < 3; i++) __ss.moveToSong(1, false, true)
        return __ss.state.move
    }""")
    wheel.settle()
    assert wheel.wheel()["selected"] - start <= 1, \
        "a held direction jumped rather than stepping"


def test_holding_steps_at_a_readable_rate(wheel):
    """Not once per auto-repeat, which is faster than it can be read."""
    wheel.settle()
    start = wheel.wheel()["selected"]
    wheel.page.evaluate("""async () => {
        for (let i = 0; i < 10; i++) {
            __ss.moveToSong(1, false, true)
            await new Promise(r => setTimeout(r, 30))
        }
    }""")
    wheel.settle()
    moved = wheel.wheel()["selected"] - start
    assert 1 <= moved <= 4, f"300ms of holding moved {moved} songs"


def test_a_deliberate_double_tap_still_jumps(wheel):
    wheel.settle()
    start = wheel.wheel()["selected"]
    skip_by = wheel.page.evaluate("() => __ss.songSelecting.skipBy")
    wheel.page.evaluate("() => __ss.moveToSong(1, false, false)")
    wheel.page.wait_for_timeout(10)
    wheel.page.evaluate("() => __ss.moveToSong(1, false, false)")
    wheel.settle()
    assert wheel.wheel()["selected"] - start == 1 + skip_by


def test_the_step_sound_thins_out_when_moving_quickly(wheel):
    """Held, a click per step runs together into a drone."""
    played = wheel.page.evaluate("""async () => {
        const real = __ss.playSound.bind(__ss)
        let kas = 0
        __ss.playSound = (id, ...rest) => { if (id === "se_ka") kas++; return real(id, ...rest) }
        try {
            for (let i = 0; i < 12; i++) {
                __ss.moveToSong(1, false, true)
                await new Promise(r => setTimeout(r, 30))
            }
            return kas
        } finally { __ss.playSound = real }
    }""")
    assert played <= 3, f"360ms of holding played {played} step sounds"


def test_the_cursor_moves_on_the_press(wheel):
    """YataiDON changes its index at once and lets the boxes catch up.

    Ours flipped it part way through the slide, which is why the sound and
    the box opening trailed the press instead of landing with it.
    """
    wheel.settle()
    moved = wheel.page.evaluate("""() => {
        const from = __ss.selectedSong
        __ss.moveToSong(1)
        return __ss.selectedSong - from   // read before any frame has run
    }""")
    assert moved == 1, "the cursor had not moved by the time the press returned"


def test_the_step_sound_plays_on_the_press(wheel):
    """It used to play when the index flipped, most of a step later."""
    wheel.settle()
    when = wheel.page.evaluate("""() => {
        const real = __ss.playSound.bind(__ss)
        let heard = null
        __ss.playSound = (id, ...rest) => {
            if (id === "se_ka" && heard === null) heard = __ss.selectedSong
            return real(id, ...rest)
        }
        try {
            __ss.lastMoveSound = 0
            const before = __ss.selectedSong
            __ss.moveToSong(1)
            return {heard: heard !== null, sameTurn: __ss.selectedSong !== before}
        } finally { __ss.playSound = real }
    }""")
    assert when["heard"] is True, "no step sound was played on the press"
    assert when["sameTurn"] is True


def test_the_box_waits_for_the_wheel_to_stop_before_opening(wheel):
    """YataiDON creates the yellow box at the press but does not start
    opening it until the box has come to rest, and then waits 133ms
    more.

    Ours started 133ms after the press, part way through a 166ms slide,
    so scrolling at any pace between the two started every box opening
    and cut it off again -- which reads as flickering rather than
    scrolling."""
    timing = wheel.page.evaluate("""() => {
        const s = __ss.songSelecting
        __ss.moveToSong(1)
        return {
            wait: __ss.state.expandMS - __ss.state.moveMS,
            duration: s.expandDuration,
            slide: s.speed,
            delay: s.expandDelay,
        }
    }""")
    wheel.settle()
    assert timing["wait"] == timing["slide"] + timing["delay"]
    assert timing["duration"] == 233
    assert timing["wait"] > timing["slide"], "it starts before the slide ends"


def test_a_category_jump_lands_rather_than_sliding(wheel):
    """It crosses a whole category; sliding the whole way is a blur."""
    wheel.leave_folder()
    wheel.settle()
    state = wheel.page.evaluate("""() => {
        __ss.categoryJump(1)
        return {slide: __ss.state.slide, locked: __ss.state.locked}
    }""")
    assert state["slide"] == 0
    assert state["locked"] == 0
    assert wheel.errors == []


def test_a_jump_lands_and_opens_without_waiting(wheel):
    """Nothing slides on a jump, so there is nothing to wait for."""
    timings = wheel.page.evaluate("""() => {
        __ss.categoryJump(1)
        return {
            wait: __ss.state.expandMS - __ss.state.moveMS,
            delay: __ss.songSelecting.expandDelay
        }
    }""")
    assert timings["wait"] == timings["delay"]


def test_scrolling_past_a_song_never_opens_it(wheel):
    """Held input repeats every 110ms and the box needs 299ms of quiet,
    so a run through the list opens nothing on the way."""
    unopened = wheel.page.evaluate("""() => {
        const start = __ss.getMS()
        let ms = start
        let opened = 0
        for(let i = 0; i < 8; i++){
            __ss.state.moveMS = ms
            __ss.state.expandMS = ms + __ss.expandStart(false)
            ms += __ss.songSelecting.repeatInterval
            if(ms >= __ss.state.expandMS) opened++
        }
        return opened
    }""")
    assert unopened == 0
