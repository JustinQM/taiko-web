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
    assert state["total"] > 0
    assert wheel.errors == [], f"song select raised: {wheel.errors}"


def test_every_song_is_reachable_through_a_genre_folder(wheel):
    """No song is stranded: the genre folders partition all of them."""
    counts = wheel.page.evaluate("""() => {
        const folders = __ss.navigator.items.filter(i => i.action === "folder")
        const inFolders = folders.reduce((n, f) => n + f.folder.songs.length, 0)
        const ids = new Set()
        for (const f of folders) for (const s of f.folder.songs) ids.add(s.id)
        return {songs: assets.songs.length, inFolders: inFolders, distinct: ids.size}
    }""")
    assert counts["inFolders"] == counts["songs"]
    assert counts["distinct"] == counts["songs"], "a song is in two folders"


def test_root_is_folders_then_menu_entries(wheel):
    """YataiDON's ordering: genres first, menu entries last."""
    root = wheel.page.evaluate(
        "() => __ss.navigator.items.map(i => i.action || 'song')")
    folders = [i for i, a in enumerate(root) if a == "folder"]
    actions = [i for i, a in enumerate(root) if a not in ("folder", "song")]
    assert folders == list(range(len(folders))), \
        f"the genre folders are not first: {root}"
    assert min(actions) > max(folders), "a menu entry is above a genre"
    assert "song" not in root, "a bare song is loose at the root"


def test_the_root_has_no_back_box(wheel):
    """There is nothing above the root to go back to."""
    assert wheel.page.evaluate(
        "() => __ss.navigator.items.some(i => i.action === 'back')") is False


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
    """Songs live inside genre folders now, so descend to reach one."""
    wheel.enter_folder()
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
            // a real song, which lives inside a folder now
            const folder = __ss.navigator.items.find(i => i.action === "folder")
            by.aSong = __ss.entryDisabledInSession(folder.folder.songs[0])
            by.aFolder = __ss.entryDisabledInSession(folder)
            return by
        } finally { p2.session = real }
    }""")
    assert disabled["search"] is False, "Search still renders as disabled in a session"
    assert disabled["random"] is False
    assert disabled["aSong"] is False, "an ordinary song must stay selectable"
    assert disabled["aFolder"] is False, \
        "folders are usable in a session now that the path travels with the selection"
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


def test_genre_order_matches_the_old_category_order(wheel):
    """Folders appear in the order the categories used to run in.

    The wheel has gone from runs within one list to folders; the order
    they come in should not have changed with it.
    """
    shape = wheel.page.evaluate("""() => {
        const items = __ss.navigator.items
        return {
            // genre folders only; collections like favourites sit after
            // them and are not categories
            genres: items.filter(i => i.folder && i.folder.id.startsWith("genre:"))
                         .map(i => i.originalCategory),
            actions: items.filter(i => i.action && i.action !== "folder").map(i => i.action),
        }
    }""")
    assert shape["genres"][0] == "Pop"
    assert shape["genres"][-1] == "創作譜面"
    assert shape["actions"] == ["random", "search", "tutorial", "about",
                                "settings"]

# What toSelectDifficulty actually does with each kind of entry during a
# session, rather than what the predicate returns. Testing only the
# predicate is what let an inverted branch through once already.
DISPATCH = """
(action) => {
    const realSession = p2.session, realSend = p2.send
    const sent = []
    const before = {screen: __ss.state.screen, search: !!__ss.search}
    try {
        p2.session = true
        p2.send = (type, value) => sent.push(type)
        __ss.state.selLock = false
        __ss.state.locked = 0
        const index = action === null
            ? __ss.songs.findIndex(s => s.courses)
            : __ss.songs.findIndex(s => s.action === action)
        // songs live inside folders; the caller descends first for those
        if (index < 0) return null
        __ss.selectedSong = index
        __ss.state.move = 0
        __ss.toSelectDifficulty()
        return {
            sentSongsel: sent.includes("songsel"),
            openedDifficulty: __ss.state.screen === "difficulty" && before.screen !== "difficulty",
            openedSearch: !!__ss.search && !before.search,
            // clean() stops the redraw loop, so this catches an entry
            // navigating away to another screen entirely
            leftSongSelect: __ss.redrawRunning === false,
        }
    } finally {
        p2.session = realSession
        p2.send = realSend
        __ss.removeSearch && __ss.removeSearch()
        __ss.state.screen = "song"
    }
}
"""


@pytest.fixture
def dispatch(wheel):
    def run(action):
        return wheel.page.evaluate(DISPATCH, action)
    return run


def test_a_song_is_sent_to_the_peer_not_opened_locally(wheel, dispatch):
    """Both clients open difficulty select together, on the peer's echo."""
    wheel.enter_folder()
    result = dispatch(None)
    assert result["sentSongsel"] is True, "the peer was never told"
    assert result["openedDifficulty"] is False, "opened locally, ahead of the peer"


def test_search_opens_locally_in_a_session(dispatch):
    """Search re-enters here with a real song once something is chosen,
    and that selection is what syncs."""
    result = dispatch("search")
    assert result["openedSearch"] is True, "Search did nothing in a session"


def test_random_is_not_swallowed_in_a_session(dispatch):
    """Random picks an index locally and moves to it; the move syncs."""
    result = dispatch("random")
    assert result["sentSongsel"] is False, "random should not send a selection itself"


@pytest.mark.parametrize("action", ["settings", "about", "tutorial"])
def test_blocked_entries_do_nothing_in_a_session(dispatch, action):
    result = dispatch(action)
    if result is None:
        pytest.skip(f"no {action} entry in this build")
    assert result["sentSongsel"] is False
    assert result["openedDifficulty"] is False
    assert result["openedSearch"] is False
    assert result["leftSongSelect"] is False, \
        f"{action} navigated away during a session instead of being ignored"
