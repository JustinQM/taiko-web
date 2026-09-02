"""Descending into folders and coming back out.

The wheel is no longer one flat list: the root holds genre folders, and
the songs live inside them. What the renderer sees is still a flat array
-- a folder listing is one too -- so these are about the navigator's
bookkeeping and about what SongSelect resets when the listing changes
underneath it.
"""

import pytest


@pytest.fixture
def wheel(game):
    return game.open_song_select()


def test_entering_a_folder_lists_its_songs(wheel):
    root_total = wheel.wheel()["total"]
    wheel.enter_folder()
    inside = wheel.page.evaluate("""() => ({
        path: __ss.navigator.path.map(f => f.id),
        total: __ss.songs.length,
        first: __ss.songs[0].action,
        allSongs: __ss.songs.slice(1).every(s => !!s.courses),
    })""")
    assert inside["path"] == ["genre:Pop"]
    assert inside["first"] == "back", "a folder listing starts with a back box"
    assert inside["allSongs"], "a folder holds songs and nothing else"
    assert inside["total"] > root_total


def test_the_cursor_lands_on_a_song_not_the_back_box(wheel):
    wheel.enter_folder()
    assert wheel.wheel()["selected"] == 1


def test_leaving_returns_to_the_folder_you_came_from(wheel):
    wheel.select_index(2)
    wheel.page.evaluate("() => __ss.toFolder()")
    wheel.page.wait_for_function("() => __ss.navigator.path.length > 0")
    wheel.leave_folder()
    state = wheel.wheel()
    assert state["selected"] == 2, "came back somewhere other than the folder left"
    assert state["action"] == "folder"


def test_reopening_a_folder_returns_to_where_you_were(wheel):
    """YataiDON remembers this per folder and it matters a lot in use."""
    wheel.enter_folder()
    wheel.select_index(40)
    title = wheel.wheel()["title"]
    wheel.leave_folder()
    wheel.enter_folder()
    assert wheel.wheel()["selected"] == 40, "did not return to the same song"
    assert wheel.wheel()["title"] == title


def test_leaving_the_root_is_not_possible(wheel):
    """The root has no back box, so nothing can ascend out of it."""
    assert wheel.page.evaluate("() => __ss.navigator.back(0)") is None


def test_a_song_inside_a_folder_opens_difficulty_select(wheel):
    wheel.enter_folder()
    wheel.page.evaluate("() => __ss.toSelectDifficulty()")
    wheel.page.wait_for_function("() => __ss.state.screen === 'difficulty'", timeout=5000)
    wheel.page.evaluate("() => __ss.toSongSelect()")
    wheel.page.wait_for_function("() => __ss.state.screen === 'song'", timeout=5000)
    assert wheel.errors == []


def test_changing_listing_clears_the_move_in_flight(wheel):
    """The move animation indexes into the old listing; it cannot survive."""
    wheel.page.evaluate("() => __ss.moveToSong(1)")
    wheel.enter_folder()
    state = wheel.page.evaluate("""() => ({
        move: __ss.state.move, locked: __ss.state.locked, hover: __ss.state.moveHover,
    })""")
    assert state["move"] == 0
    assert state["locked"] == 0
    assert state["hover"] is None


def test_random_reaches_a_song_from_the_root(wheel):
    """The root holds no songs, so picking one out of the current listing
    could never terminate -- it used to hang the page outright."""
    target = wheel.page.evaluate("() => __ss.navigator.randomSong()")
    assert target is not None
    assert target["index"] >= 1, "landed on the back box"

    wheel.page.evaluate(
        "t => __ss.enterListing(__ss.navigator.jumpTo(t.rootIndex, t.index))", target)
    landed = wheel.wheel()
    assert landed["action"] is None, f"random landed on {landed['action']}"
    assert wheel.page.evaluate("() => __ss.navigator.path.length") == 1


def test_random_lands_somewhere_different_over_many_tries(wheel):
    picks = wheel.page.evaluate("""() => {
        const out = new Set()
        for (let i = 0; i < 40; i++) {
            const t = __ss.navigator.randomSong()
            out.add(t.rootIndex + ":" + t.index)
        }
        return out.size
    }""")
    assert picks > 20, f"40 draws produced only {picks} distinct songs"


def test_category_jump_inside_a_folder_pages(wheel):
    """Everything in a folder shares its category, so there are no runs to
    step between; it jumps a page instead."""
    wheel.enter_folder()
    wheel.select_index(1)
    skip_by = wheel.page.evaluate("() => __ss.songSelecting.skipBy")
    wheel.page.evaluate("() => __ss.categoryJump(1)")
    wheel.settle()
    assert wheel.wheel()["selected"] == 1 + skip_by


def test_folders_are_refused_during_a_session(wheel):
    """Neither peer can descend until the path travels with the selection,
    so both keep the identical listing."""
    blocked = wheel.page.evaluate("""() => {
        const real = p2.session
        try {
            p2.session = true
            __ss.selectedSong = 0
            __ss.toFolder()
            return __ss.navigator.path.length
        } finally { p2.session = real }
    }""")
    assert blocked == 0, "a folder was entered during a session"
