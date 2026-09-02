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
        "t => __ss.enterListing(__ss.navigator.jumpToPath(t.path, t.index))", target)
    landed = wheel.wheel()
    assert landed["action"] is None, f"random landed on {landed['action']}"
    assert wheel.page.evaluate("() => __ss.navigator.path.length") >= 1


def test_random_lands_somewhere_different_over_many_tries(wheel):
    picks = wheel.page.evaluate("""() => {
        const out = new Set()
        for (let i = 0; i < 40; i++) {
            const t = __ss.navigator.randomSong()
            if (!t) return -1     // every song must be reachable
            out.add(t.path.join("/") + ":" + t.index)
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


def test_nesting_comes_from_the_source_tree(wheel):
    """Sub-folders are the path the chart had on disk, below its genre.

    Most songs have none, so most genres stay flat. The ones that do get
    the structure they were organised with.
    """
    nested = wheel.page.evaluate("""() => {
        const out = []
        for (const item of __ss.navigator.items) {
            if (!item.folder || !item.folder.children) continue
            out.push({
                genre: item.folder.id,
                children: item.folder.children.map(c => ({id: c.id, songs: c.songs.length})),
            })
        }
        return out
    }""")
    if not nested:
        pytest.skip("this database has no songs with a folder path")
    assert any(c["songs"] > 1 for n in nested for c in n["children"])


def test_a_nested_folder_can_be_opened(wheel):
    index = wheel.page.evaluate(
        "() => __ss.navigator.items.findIndex(i => i.folder && i.folder.children)")
    if index < 0:
        pytest.skip("this database has no nested folders")

    wheel.enter_folder(index)
    child = wheel.page.evaluate(
        "() => __ss.songs.findIndex(s => s.action === 'folder')")
    assert child > 0, "the sub-folder is not listed above the songs"

    wheel.select_index(child)
    wheel.page.evaluate("() => __ss.toFolder()")
    wheel.page.wait_for_function("() => __ss.navigator.path.length === 2", timeout=5000)
    assert wheel.page.evaluate("() => __ss.songs.slice(1).every(s => !!s.courses)")
    assert wheel.errors == []


def test_leaving_a_nested_folder_goes_up_one_level(wheel):
    index = wheel.page.evaluate(
        "() => __ss.navigator.items.findIndex(i => i.folder && i.folder.children)")
    if index < 0:
        pytest.skip("this database has no nested folders")
    wheel.enter_folder(index)
    child = wheel.page.evaluate("() => __ss.songs.findIndex(s => s.action === 'folder')")
    wheel.select_index(child)
    wheel.page.evaluate("() => __ss.toFolder()")
    wheel.page.wait_for_function("() => __ss.navigator.path.length === 2", timeout=5000)

    wheel.select_index(0)
    wheel.page.evaluate("() => __ss.toFolderUp()")
    wheel.page.wait_for_function("() => __ss.navigator.path.length === 1", timeout=5000)
    assert wheel.wheel()["selected"] == child, "did not land back on the sub-folder"


def test_a_song_property_cannot_be_mistaken_for_a_folder(wheel):
    """Songs carry their source path too; it must not look like a folder."""
    clean = wheel.page.evaluate(
        "() => __ss.navigator.songItems.every(s => s.folder === undefined)")
    assert clean is True, "a song still has a .folder, which folder items use"


def test_random_can_reach_a_nested_song(wheel):
    """Songs below their genre were unreachable when nesting arrived: the
    lookup only searched the top level of each genre and gave up."""
    nested = wheel.page.evaluate("""() => {
        for (const item of __ss.navigator.items) {
            const f = item.folder
            if (f && f.children && f.children.length && f.children[0].songs.length)
                return f.children[0].songs[0].id
        }
        return null
    }""")
    if nested is None:
        pytest.skip("this database has no nested songs")

    target = wheel.page.evaluate("""id => {
        const song = __ss.navigator.songItems.find(s => s.id === id)
        return __ss.navigator.locate(song)
    }""", nested)
    assert target is not None, "a nested song could not be located"
    assert len(target["path"]) == 2, f"expected a two-level path, got {target['path']}"

    index = wheel.page.evaluate(
        "t => __ss.navigator.jumpToPath(t.path, t.index)", target)
    landed = wheel.page.evaluate("i => __ss.navigator.items[i].id", index)
    assert landed == nested, "landed on the wrong song"
