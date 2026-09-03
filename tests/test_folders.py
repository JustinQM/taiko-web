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
        // songs, with a way back out interleaved through them
        kinds: [...new Set(__ss.songs.slice(1).map(s => s.action || "song"))].sort(),
    })""")
    assert inside["path"] == ["genre:Pop"]
    assert inside["kinds"] == ["back", "song"], f"unexpected entries: {inside['kinds']}"
    assert inside["first"] == "back", "a folder listing starts with a back box"
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


def test_a_way_out_appears_every_ten_songs(wheel):
    """One back box at the top of several hundred songs is not a way out."""
    wheel.enter_folder()
    layout = wheel.page.evaluate("""() => {
        const backs = []
        __ss.songs.forEach((s, i) => { if (s.action === "back") backs.push(i) })
        return {backs: backs.slice(0, 6), total: __ss.songs.length,
                every: SongNavigator.backEvery}
    }""")
    assert layout["backs"][0] == 0
    gaps = [b - a for a, b in zip(layout["backs"], layout["backs"][1:])]
    assert set(gaps) == {layout["every"] + 1}, \
        f"back boxes are not evenly spaced: {layout['backs']}"


def test_the_interleaved_back_boxes_still_ascend(wheel):
    wheel.enter_folder()
    second = wheel.page.evaluate(
        "() => __ss.songs.findIndex((s, i) => i > 0 && s.action === 'back')")
    wheel.select_index(second)
    wheel.page.evaluate("() => __ss.toSelectDifficulty()")
    wheel.page.wait_for_function("() => __ss.navigator.path.length === 0", timeout=5000)
    assert wheel.errors == []


def test_random_still_lands_on_its_song_with_backs_interleaved(wheel):
    """The listing offset is no longer a simple count, so it is asked for
    rather than worked out."""
    for _ in range(5):
        target = wheel.page.evaluate("() => __ss.navigator.randomSong()")
        landed = wheel.page.evaluate("""t => {
            const i = __ss.navigator.jumpToPath(t.path, t.index)
            return __ss.navigator.items[i].action || "song"
        }""", target)
        assert landed == "song", f"random landed on a {landed}"


def test_a_folder_is_drawn_at_its_full_width(wheel):
    """A folder and a song looked the same in the wheel -- an 82px slat
    with the name down it, differing only in colour -- so there was no
    way to see at a glance where the folders were."""
    widths = wheel.page.evaluate("""() => {
        const folder = __ss.songs.find(s => s.action === "folder")
        const menu = __ss.songs.find(s => s.action && s.action !== "folder")
        return {
            folder: __ss.entryWidth(folder),
            menu: __ss.entryWidth(menu),
            slat: __ss.songAsset.width,
            opened: __ss.songAsset.selectedWidth
        }
    }""")
    assert widths["folder"] == widths["opened"]
    assert widths["menu"] == widths["slat"], "menu entries stay slats"


def test_the_wheel_makes_room_for_a_wide_folder(wheel):
    """Boxes used to be placed by multiplying their index by one width.
    With folders at a different width that stops being true, so the
    layout is walked -- and every box has to end up clear of the one
    before it."""
    boxes = wheel.page.evaluate("""() => {
        const layout = __ss.wheelLayout(__ss.selectedEntryWidth(), 0, 1280)
        return layout.left.concat([layout.selected], layout.right)
            .map(b => ({x: b.x, w: b.width, offset: b.offset}))
            .sort((a, b) => a.x - b.x)
    }""")
    assert len(boxes) > 3
    margin = wheel.page.evaluate("() => __ss.songAsset.marginLeft")
    for before, after in zip(boxes, boxes[1:]):
        gap = after["x"] - (before["x"] + before["w"])
        assert abs(gap - margin) < 0.01, f"gap of {gap} between {before} and {after}"


def test_clicking_past_a_folder_selects_what_was_clicked(wheel):
    """The mouse used to divide by a fixed box width, which a folder
    between the cursor and the pointer would throw out."""
    agreed = wheel.page.evaluate("""() => {
        const layout = __ss.wheelLayout(__ss.selectedEntryWidth(), 0, 1280)
        const boxes = layout.left.concat([layout.selected], layout.right)
        const y = __ss.songAsset.marginTop + 10
        return boxes.map(b => ({
            offset: b.offset,
            hit: __ss.songSelMouse(b.x + b.width / 2, y)
        }))
    }""")
    assert agreed, "no boxes to click"
    for box in agreed:
        assert box["hit"] == box["offset"], f"clicking {box['offset']} gave {box['hit']}"


def test_the_position_in_the_folder_is_shown(wheel):
    """A folder holds hundreds of songs and shows seven of them."""
    wheel.enter_folder()
    wheel.settle()
    shown = wheel.page.evaluate("""() => {
        const seen = []
        const real = __ss.draw.layeredText
        __ss.draw.layeredText = function(config, layers){
            seen.push(config.text)
            return real.call(this, config, layers)
        }
        try { __ss.redraw() } finally { __ss.draw.layeredText = real }
        return seen.filter(t => / \\/ /.test(t))
    }""")
    assert len(shown) == 1, f"expected one position counter, saw {shown}"
    position, total = [int(part) for part in shown[0].split(" / ")]
    assert position >= 1 and total > position


def test_the_position_counts_songs_rather_than_entries(wheel):
    """Back boxes are interleaved every ten songs and are not songs."""
    wheel.enter_folder()
    wheel.settle()
    counted = wheel.page.evaluate("""() => {
        let text = null
        const real = __ss.draw.layeredText
        __ss.draw.layeredText = function(config, layers){
            if(/ \\/ /.test(config.text)) text = config.text
            return real.call(this, config, layers)
        }
        try { __ss.redraw() } finally { __ss.draw.layeredText = real }
        return {
            text: text,
            entries: __ss.songs.length,
            songs: __ss.songs.filter(s => !s.action).length
        }
    }""")
    assert counted["text"].endswith("/ " + str(counted["songs"]))
    assert counted["songs"] < counted["entries"], "no back boxes to exclude"


def test_no_position_at_the_root(wheel):
    """The root is folders and menu items; a position among those means
    nothing."""
    shown = wheel.page.evaluate("""() => {
        const seen = []
        const real = __ss.draw.layeredText
        __ss.draw.layeredText = function(config, layers){
            seen.push(config.text)
            return real.call(this, config, layers)
        }
        try { __ss.redraw() } finally { __ss.draw.layeredText = real }
        return seen.filter(t => / \\/ /.test(t))
    }""")
    assert shown == []


CROWN_SPY = """() => {
    window.__crowns = []
    const real = __ss.draw.crown
    __ss.draw.crown = function(config){
        window.__crowns.push({size: config.size, variant: config.variant, y: config.y})
        return real.call(this, config)
    }
    __ss.redraw()
    __ss.draw.crown = real
    return window.__crowns
}"""


@pytest.fixture
def scored(wheel):
    """Inside a folder, on a song with a crown on every difficulty."""
    wheel.enter_folder()
    wheel.page.evaluate("""() => {
        const fake = {}
        for(const d of ["easy", "normal", "hard", "oni"]) fake[d] = {crown: "gold"}
        scoreStorage.get = () => fake
        scoreStorage.getP2 = () => fake
    }""")
    wheel.settle()
    return wheel


def test_crowns_are_drawn_at_the_skins_sizes(scored):
    """They were drawn as a fraction of the fallback path's box, which
    made both of them small: 23px inside the opened box where the skin
    has 56, and 28 above a closed one where the skin has 40.

    48 rather than 56 in the opened box: the skin packs them 60 apart on
    the difficulty screen too, but ours sit 60 apart in the box itself,
    where 56 leaves the outlines touching."""
    sizes = {(c["variant"], c["size"]) for c in scored.page.evaluate(CROWN_SPY)}
    assert ("box", 48) in sizes, sizes
    assert ("small", 40) in sizes, sizes


def test_crowns_shrink_when_two_players_share_the_row(scored):
    """In a session each difficulty carries two crowns side by side, and
    two of the skin's do not fit."""
    scored.page.evaluate("() => { p2.session = true; p2.player = 1 }")
    sizes = {(c["variant"], c["size"]) for c in scored.page.evaluate(CROWN_SPY)}
    assert all(size <= 28 for _, size in sizes), sizes
    assert all(variant == "small" for variant, _ in sizes), sizes


def test_search_opens_the_song_it_found(wheel):
    """Search looks through the whole library; the wheel holds one folder
    of it. This looked for the chosen song in the current listing, found
    nothing, and set the cursor to -1 -- so picking a result did nothing
    at all."""
    wanted = wheel.page.evaluate("""() => {
        const song = __ss.navigator.songItems[400] || __ss.navigator.songItems[0]
        __ss.searchProceed(song.id)
        return song.title
    }""")
    wheel.page.wait_for_function(
        "() => __ss.state.screen === 'difficulty'", timeout=8000)
    landed = wheel.page.evaluate("""() => ({
        title: __ss.songs[__ss.selectedSong].title,
        path: __ss.navigator.pathIds()
    })""")
    assert landed["title"] == wanted
    assert landed["path"], "the song's folder was never opened"


def test_search_from_inside_another_folder(wheel):
    """The folder it lands in is rarely the one it was searched from."""
    wheel.enter_folder()
    wheel.settle()
    result = wheel.page.evaluate("""() => {
        const here = __ss.navigator.pathIds()
        const song = __ss.navigator.songItems.find(s => {
            const t = __ss.navigator.locate(s)
            return t && JSON.stringify(t.path) !== JSON.stringify(here)
        })
        __ss.searchProceed(song.id)
        return {wanted: song.title, from: here}
    }""")
    wheel.page.wait_for_function(
        "() => __ss.state.screen === 'difficulty'", timeout=8000)
    landed = wheel.page.evaluate("""() => ({
        title: __ss.songs[__ss.selectedSong].title,
        path: __ss.navigator.pathIds()
    })""")
    assert landed["title"] == result["wanted"]
    assert landed["path"] != result["from"]


def test_the_wheel_travels_the_distance_it_actually_covers(wheel):
    """A step used to be one box width, which was true while every box
    was one width. A folder is nearly five of them, so stepping onto one
    slid a hundred pixels and jumped the other three hundred."""
    measured = wheel.page.evaluate("""() => {
        const slat = __ss.songAsset.width
        const block = __ss.songAsset.selectedWidth
        const margin = __ss.songAsset.marginLeft
        // Onto a folder, and between two folders: the root is folders
        // and menu entries, so both cases are here.
        const folders = __ss.songs.map((s, i) => __ss.entryIsFolder(s) ? i : -1)
            .filter(i => i >= 0)
        const between = folders.find(i => folders.includes(i + 1))
        __ss.selectedSong = between + 1
        const folderToFolder = Math.abs(__ss.slidePixels(1))
        const menu = __ss.songs.findIndex(s => s.action && s.action !== "folder")
        __ss.selectedSong = menu + 1
        const menuToMenu = Math.abs(__ss.slidePixels(-1))
        return {folderToFolder, menuToMenu, slat, block, margin}
    }""")
    assert measured["folderToFolder"] == measured["block"] + measured["margin"]
    assert measured["menuToMenu"] == measured["slat"] + measured["margin"]
