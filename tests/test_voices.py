"""Which voice calls out a result, and which voices are gone.

Upstream shipped synthesised stand-ins for the lines it could not
distribute. Most have been replaced by the skin's own; these are about
the ones that were dropped rather than replaced, and about the results
screen now having a line per outcome instead of one generic announcement.

The mapping lives in Scoresheet.resultVoice, which is a pure decision and
so can be asked directly. Whether it sounds right is not something a test
can hold -- that a donderful and a full combo no longer share a line is.
"""

import pytest


@pytest.fixture
def sheet(game):
    """The client loaded far enough to have Scoresheet and its sounds."""
    game.page.wait_for_function(
        "() => typeof Scoresheet !== 'undefined' && typeof assets !== 'undefined'",
        timeout=40000)
    return game


def voice(sheet, crown, gauge):
    return sheet.page.evaluate(
        "([c, g]) => Scoresheet.prototype.resultVoice(c, g)", [crown, gauge])


# --------------------------------------------------------- the ladder


def test_a_donderful_no_longer_sounds_like_a_full_combo(sheet):
    """They shared v_results_fullcombo, with a TODO saying so."""
    assert voice(sheet, "rainbow", 1) == "v_donderful"
    assert voice(sheet, "gold", 1) == "v_results_fullcombo"
    assert voice(sheet, "rainbow", 1) != voice(sheet, "gold", 1)


def test_every_outcome_has_its_own_line(sheet):
    lines = {
        "donderful": voice(sheet, "rainbow", 1),
        "full combo": voice(sheet, "gold", 1),
        "clear": voice(sheet, "silver", 1),
        "fail": voice(sheet, None, 0.8),
        "bad fail": voice(sheet, None, 0.1),
    }
    assert len(set(lines.values())) == len(lines), lines


def test_a_fail_splits_on_half_the_gauge(sheet):
    """The skin's own script splits it here: not making it at all and
    nearly making it are different disappointments."""
    assert voice(sheet, None, 0.49) == "v_results_maxfail"
    assert voice(sheet, None, 0.50) == "v_results_fail"
    assert voice(sheet, None, 0.99) == "v_results_fail"


def test_a_clear_is_a_clear_however_full_the_gauge(sheet):
    """The gauge only decides between the two fails."""
    assert voice(sheet, "silver", 0.1) == voice(sheet, "silver", 1.0)


# ------------------------------------------------------- what is loaded


def test_every_line_the_ladder_names_is_loaded(sheet):
    """Including the second-player copies, which are picked by name."""
    missing = sheet.page.evaluate("""() => {
        const base = ["v_donderful", "v_results_fullcombo", "v_results_clear",
                      "v_results_fail", "v_results_maxfail", "v_results_highscore"]
        return base.concat(base.map(n => n + "2")).filter(n => !assets.sounds[n])
    }""")
    assert missing == []


def test_the_dropped_lines_are_not_loaded(sheet):
    """The title screen's, the drumroll call and the generic results
    announcement are gone rather than replaced -- the skin has no
    equivalent for any of them, and a line that means something else is
    worse than none."""
    still_here = sheet.page.evaluate(
        """() => ["v_title", "v_renda", "v_results"].filter(n => assets.sounds[n])""")
    assert still_here == []


def test_nothing_still_asks_for_them(sheet):
    """A sound that is not loaded but still played throws on the frame it
    would have played, which is the middle of a song."""
    assert sheet.page.evaluate("""() => assets.audioSfx
        .concat(assets.audioSfxLR, assets.audioSfxLoud)
        .filter(n => ["v_title.ogg", "v_renda.ogg", "v_results.ogg"].includes(n))""") == []


def test_the_netplay_line_is_deliberately_still_there(sheet):
    """v_sanka is the last synthesised line. It only plays when a session
    starts while the window is unfocused, and the skin has no netplay to
    have a voice for -- so it stays until there is something to put in
    its place."""
    assert sheet.page.evaluate("() => !!assets.sounds['v_sanka']") is True
