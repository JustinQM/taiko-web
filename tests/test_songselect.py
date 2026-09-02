"""Song select as it behaves today.

This is the regression net for turning the flat wheel into a folder tree.
It deliberately pins the current structure -- one flat array of every
song, grouped by category -- so that the no-op navigator refactor has
something to prove itself against, and so the stage that changes the
structure has to change these tests deliberately rather than silently.
"""

import pytest


@pytest.fixture
def wheel(game):
    return game.open_song_select()


def test_song_select_opens_without_errors(wheel):
    state = wheel.wheel()
    assert state["screen"] == "song"
    assert state["total"] > 3000, f"only {state['total']} entries in the wheel"
    assert wheel.errors == [], f"song select raised: {wheel.errors}"


def test_every_song_is_in_the_wheel(wheel):
    """Flat: one entry per song, plus the menu entries after them."""
    counts = wheel.page.evaluate("""() => ({
        songs: assets.songs.length,
        entries: __ss.songs.length,
        withCourses: __ss.songs.filter(s => s.courses).length,
        actions: __ss.songs.filter(s => s.action).map(s => s.action),
    })""")
    assert counts["withCourses"] == counts["songs"]
    assert counts["entries"] == counts["songs"] + len(counts["actions"])


def test_menu_entries_come_last_and_in_order(wheel):
    actions = wheel.page.evaluate(
        "() => __ss.songs.map((s, i) => s.action ? [i, s.action] : null).filter(Boolean)"
    )
    indexes = [i for i, _ in actions]
    assert indexes == sorted(indexes)
    assert indexes[0] == wheel.wheel()["total"] - len(actions), \
        "menu entries are not contiguous at the end of the wheel"
    assert [a for _, a in actions][:2] == ["random", "search"]


def test_songs_are_grouped_by_category(wheel):
    """Each category occupies one contiguous run.

    This is what the wheel's colour bands rely on, and it is the invariant
    the folder tree replaces.
    """
    runs = wheel.page.evaluate("""() => {
        const seen = [], out = []
        for (const s of __ss.songs) {
            if (!s.courses) break
            if (out.length === 0 || out[out.length - 1] !== s.originalCategory)
                out.push(s.originalCategory)
        }
        return out
    }""")
    assert len(runs) == len(set(runs)), f"a category appears in two runs: {runs}"


def test_moving_changes_the_selection(wheel):
    before = wheel.wheel()["selected"]
    wheel.move(1)
    assert wheel.wheel()["selected"] == before + 1
    wheel.move(-1)
    assert wheel.wheel()["selected"] == before
    assert wheel.errors == []


def test_moving_wraps_around_the_end(wheel):
    total = wheel.wheel()["total"]
    wheel.select_index(total - 1)
    wheel.move(1)
    assert wheel.wheel()["selected"] == 0, "the wheel did not wrap"


def test_category_jump_lands_on_a_different_category(wheel):
    wheel.select_index(0)
    start = wheel.wheel()["category"]
    wheel.category_jump(1)
    after = wheel.wheel()
    assert after["category"] != start, f"still in {start}"
    assert after["selected"] != 0


def test_selecting_a_song_opens_difficulty_select(wheel):
    """The first entry is a song, so it has courses and can be entered."""
    wheel.select_index(0)
    wheel.page.evaluate("() => __ss.toSelectDifficulty()")
    wheel.page.wait_for_function("() => __ss.state.screen === 'difficulty'", timeout=5000)
    assert wheel.wheel()["screen"] == "difficulty"

    wheel.page.evaluate("() => __ss.toSongSelect()")
    wheel.page.wait_for_function("() => __ss.state.screen === 'song'", timeout=5000)
    assert wheel.errors == []


def test_search_is_usable_in_a_netplay_session(wheel):
    """Selectable and drawn as selectable.

    The guard in toSelectDifficulty and the three sites that grey entries
    out in redraw used to carry their own copies of this condition and
    disagreed about Search: step 1 fixed the guard, so it could be chosen
    but still rendered greyed out. They share one definition now.
    """
    disabled = wheel.page.evaluate("""() => {
        const real = p2.session
        try {
            p2.session = true
            const by = {}
            for (const action of ["random", "search", "settings", "about", "tutorial"]) {
                const song = __ss.songs.find(s => s.action === action)
                if (song) by[action] = __ss.entryDisabledInSession(song)
            }
            by.aSong = __ss.entryDisabledInSession(__ss.songs[0])
            return by
        } finally { p2.session = real }
    }""")
    assert disabled["search"] is False, "Search still renders as disabled in a session"
    assert disabled["random"] is False
    assert disabled["aSong"] is False, "an ordinary song must stay selectable"
    for action in ("settings", "about", "tutorial"):
        if action in disabled:
            assert disabled[action] is True, f"{action} should stay disabled in a session"


def test_nothing_is_disabled_outside_a_session(wheel):
    any_disabled = wheel.page.evaluate(
        "() => __ss.songs.some(s => __ss.entryDisabledInSession(s))")
    assert any_disabled is False

def test_navigator_owns_the_listing(wheel):
    """this.songs is the navigator's current listing, not its own array."""
    same = wheel.page.evaluate("() => __ss.songs === __ss.navigator.items")
    assert same is True, "SongSelect is not reading from the navigator"
    assert wheel.page.evaluate("() => __ss.navigator.path.length") == 0, \
        "the root listing should be at the root of the tree"


def test_root_listing_is_unchanged_by_the_refactor(wheel):
    """A fingerprint of the old flat list, so the no-op stays a no-op.

    Rebuilding through the navigator has to produce the same entries in
    the same order as building them inline did. Anything that changes this
    should be a stage that means to.
    """
    shape = wheel.page.evaluate("""() => {
        const items = __ss.navigator.items
        return {
            total: items.length,
            songs: items.filter(s => s.courses).length,
            actions: items.filter(s => s.action).map(s => s.action),
            firstCategory: items[0].originalCategory,
            lastCategory: items.filter(s => s.courses).slice(-1)[0].originalCategory,
            sortedIds: items.filter(s => s.courses).slice(0, 5).map(s => s.id),
        }
    }""")
    assert shape["songs"] == 3367
    assert shape["total"] == shape["songs"] + len(shape["actions"])
    assert shape["actions"] == ["random", "search", "tutorial", "about",
                                "settings", "customSongs"]
    assert shape["firstCategory"] == "Pop"
    assert shape["lastCategory"] == "創作譜面"
