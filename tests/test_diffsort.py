"""Browsing by course and star level.

YataiDON's difficulty search, transcribed: a root entry that opens a
picker rather than a folder, two screens and a confirmation prompt, and
then a folder of every chart at that one course and that one level.

The interesting part is not the drawing -- it is that the folder holds
exactly the right charts, that each course goes as far up as the library
does, and that the picker's own little state machine goes where
YataiDON's goes, fall-through and all.
"""

import pytest


@pytest.fixture
def wheel(game):
    game.open_song_select()
    game.page.evaluate("""() => {
        try { localStorage.removeItem("lastDiffSort") } catch(e) {}
    }""")
    return game


def entry(wheel):
    """Where the difficulty search sits in the root listing."""
    return wheel.page.evaluate("() => __ss.songs.findIndex(s => __ss.isDiffSortEntry(s))")


def picker(wheel):
    return wheel.page.evaluate("""() => {
        const p = __ss.diffSortSelect
        return p && {box: p.selectedBox, level: p.selectedLevel,
                     levelSelect: p.inLevelSelect,
                     confirmation: p.confirmation, confirm: p.confirmIndex}
    }""")


def open_picker(wheel):
    wheel.select_index(entry(wheel))
    wheel.page.evaluate("() => { __ss.state.locked = 0; __ss.toSelectDifficulty() }")
    wheel.page.wait_for_function("() => !!__ss.diffSortSelect", timeout=5000)
    return wheel


def press(wheel, name, times=1):
    for _ in range(times):
        wheel.page.evaluate("n => __ss.diffSortPress(n)", name)
    return wheel


def choose(wheel, course, level):
    """The whole flow, as a player walks it: course, level, confirm."""
    open_picker(wheel)
    press(wheel, "right", course + 1)
    press(wheel, "select")
    press(wheel, "right", level - 1)
    press(wheel, "select")
    press(wheel, "select")
    wheel.page.wait_for_function("() => !__ss.diffSortSelect", timeout=5000)
    return wheel


# --------------------------------------------------------------- the entry


def test_it_sits_after_search(wheel):
    """Random, Search, Diff Search, Game Settings."""
    tail = wheel.page.evaluate("() => __ss.songs.slice(-4).map(s => s.action)")
    assert tail == ["random", "search", "diffSort", "settings"]


def test_it_is_a_slim_entry_not_a_folder_box(wheel):
    """It is one of the ways of finding a song, next to Random and
    Search -- not a folder, which would promise a listing behind it that
    does not exist until the picker has been answered."""
    shape = wheel.page.evaluate("""() => {
        const item = __ss.songs.find(s => __ss.isDiffSortEntry(s))
        return {
            drawnAsFolder: __ss.entryIsFolder(item),
            width: __ss.entryWidth(item),
            slat: __ss.songAsset.width,
            hasFolder: !!item.folder
        }
    }""")
    assert shape["drawnAsFolder"] is False
    assert shape["width"] == shape["slat"], "drawn at folder width"
    assert shape["hasFolder"] is True, "nothing for the picker's answer to fill"


def test_opening_it_opens_the_picker_rather_than_a_folder(wheel):
    open_picker(wheel)
    assert wheel.path() == [], "descended into the folder instead of asking"
    assert picker(wheel) is not None


def test_the_cursor_starts_on_the_way_out(wheel):
    """YataiDON puts it on the back box, at index -1, not on Easy."""
    open_picker(wheel)
    assert picker(wheel)["box"] == -1


def test_confirming_the_way_out_leaves_the_wheel_alone(wheel):
    open_picker(wheel)
    press(wheel, "select")
    assert picker(wheel) is None
    assert wheel.path() == []
    assert wheel.wheel()["selected"] == entry(wheel)


def test_escape_leaves_the_wheel_alone(wheel):
    open_picker(wheel)
    press(wheel, "back")
    assert picker(wheel) is None
    assert wheel.path() == []


# ------------------------------------------------------------- the cursor


def test_kat_walks_the_courses_and_stops(wheel):
    open_picker(wheel)
    assert picker(wheel)["box"] == -1
    press(wheel, "left", 3)
    assert picker(wheel)["box"] == -1, "walked off the left of the back box"
    press(wheel, "right", 20)
    assert picker(wheel)["box"] == 5, "walked off the right of the last box"


def test_each_course_stops_where_the_library_does(wheel):
    """Not YataiDON's fixed 5/7/8/10/10 -- its star_limit art is five
    pre-drawn strips saying so, and ours draws that line as text, so the
    cap is the highest star the library actually has a chart at and
    nothing is out of reach."""
    expected = wheel.page.evaluate("""() => {
        const stats = __ss.navigator.diffSortStats()
        return stats.map(levels => {
            for(let l = levels.length - 1; l >= 1; l--) if(levels[l].total) return l
            return 1
        })
    }""")
    caps = []
    for course in range(5):
        open_picker(wheel)
        press(wheel, "right", course + 1)
        press(wheel, "select")
        press(wheel, "right", 30)
        caps.append(picker(wheel)["level"])
        press(wheel, "back")
    assert caps == expected
    assert max(caps) > 5, "the library has more than five-star charts"


def test_every_chart_is_reachable(wheel):
    """The point of taking the cap off: no chart sits above the picker."""
    stranded = wheel.page.evaluate("""() => {
        const limits = __ss.navigator.diffSortLimits()
        const out = []
        SongNavigator.diffSortCourses.forEach((name, course) => {
            __ss.navigator.songItems.forEach(song => {
                const chart = song.courses && song.courses[name]
                if(chart && chart.stars > limits[course]) out.push([name, chart.stars])
            })
        })
        return out
    }""")
    assert stranded == []


def test_the_level_never_starts_above_its_courses_cap(wheel):
    """The top level chosen for Oni, then back out and into Easy."""
    limits = wheel.page.evaluate("() => __ss.navigator.diffSortLimits()")
    assert limits[0] < limits[3], "this needs two courses with different caps"
    open_picker(wheel)
    press(wheel, "right", 4)
    press(wheel, "select")
    press(wheel, "right", 30)
    assert picker(wheel)["level"] == limits[3]
    # the prompt's rightmost box returns to the difficulty boxes
    press(wheel, "select")
    press(wheel, "right")
    press(wheel, "select")
    assert picker(wheel)["levelSelect"] is False
    press(wheel, "left", 3)
    press(wheel, "select")
    assert picker(wheel)["level"] == limits[0], \
        "kept a level the chosen course does not go up to"


# ------------------------------------------------------------- the prompt


def test_the_prompt_starts_on_yes(wheel):
    open_picker(wheel)
    press(wheel, "right", 4)
    press(wheel, "select")
    press(wheel, "select")
    state = picker(wheel)
    assert state["confirmation"] is True
    assert state["confirm"] == 1


def test_the_prompts_last_box_goes_back_to_the_courses(wheel):
    open_picker(wheel)
    press(wheel, "right", 4)
    press(wheel, "select")
    press(wheel, "select")
    press(wheel, "right")
    press(wheel, "select")
    state = picker(wheel)
    assert state["confirmation"] is False
    assert state["levelSelect"] is False
    assert state["box"] == 3, "lost which course was being asked about"


def test_the_prompts_first_box_goes_back_to_the_stars(wheel):
    """It falls through into level select again, as YataiDON's does."""
    open_picker(wheel)
    press(wheel, "right", 4)
    press(wheel, "select")
    press(wheel, "right", 5)
    press(wheel, "select")
    press(wheel, "left")
    press(wheel, "select")
    state = picker(wheel)
    assert state["confirmation"] is False
    assert state["levelSelect"] is True, "left the star screen entirely"
    assert state["level"] == 6, "forgot the level being confirmed"


# -------------------------------------------------------------- the result


def test_the_folder_holds_exactly_that_course_at_that_level(wheel):
    choose(wheel, 3, 10)
    result = wheel.page.evaluate("""() => {
        const songs = __ss.songs.filter(s => !s.action)
        return {
            path: __ss.navigator.pathIds(),
            count: songs.length,
            offLevel: songs.filter(s => !s.courses.oni || s.courses.oni.stars !== 10).length,
            expected: __ss.navigator.diffSortStats()[3][10].total
        }
    }""")
    assert result["path"] == ["collection:diffsort"]
    assert result["offLevel"] == 0, "a chart that is not ten-star Oni got in"
    assert result["count"] == result["expected"] > 0


def test_it_reaches_across_every_genre(wheel):
    """The point of it: not a genre folder filtered, the whole library."""
    choose(wheel, 3, 10)
    genres = wheel.page.evaluate("""() => [...new Set(
        __ss.songs.filter(s => !s.action).map(s => s.originalCategory))].length""")
    assert genres > 1


def test_there_is_a_way_out_every_ten_songs(wheel):
    choose(wheel, 3, 10)
    counted = wheel.page.evaluate("""() => {
        let run = 0, worst = 0
        for(const item of __ss.songs){
            if(item.action === "back"){ run = 0 } else { run++; worst = Math.max(worst, run) }
        }
        return worst
    }""")
    assert counted <= 10


def test_the_stats_agree_with_what_the_folder_holds(wheel):
    """Every cell of the panel, against the query it describes."""
    mismatched = wheel.page.evaluate("""() => {
        const bad = []
        const stats = __ss.navigator.diffSortStats()
        const limits = __ss.navigator.diffSortLimits(stats)
        SongNavigator.diffSortCourses.forEach((name, course) => {
            const cap = limits[course]
            for(let level = 1; level <= cap; level++){
                const got = __ss.navigator.diffSortSongs(course, level).length
                if(got !== stats[course][level].total){
                    bad.push([name, level, got, stats[course][level].total])
                }
            }
        })
        return bad
    }""")
    assert mismatched == []


# ------------------------------------------------------- doing it again


def test_the_last_box_repeats_the_last_search(wheel):
    choose(wheel, 3, 9)
    wheel.leave_folder()
    open_picker(wheel)
    press(wheel, "right", 6)
    press(wheel, "select")
    wheel.page.wait_for_function("() => !__ss.diffSortSelect", timeout=5000)
    assert wheel.page.evaluate("() => __ss.navigator.diffSort") == {"course": 3, "level": 9}
    assert wheel.path() == ["collection:diffsort"]


def test_the_last_box_with_nothing_to_repeat_backs_out(wheel):
    open_picker(wheel)
    press(wheel, "right", 6)
    press(wheel, "select")
    assert picker(wheel) is None
    assert wheel.path() == []


def test_a_different_search_does_not_land_on_the_old_cursor(wheel):
    """The remembered position belongs to the songs that were there."""
    choose(wheel, 3, 10)
    wheel.select_index(30)
    wheel.leave_folder()
    choose(wheel, 0, 1)
    assert wheel.wheel()["selected"] == 1, "reopened onto a cursor from the last search"


def test_the_same_search_twice_comes_back_to_where_you_were(wheel):
    choose(wheel, 3, 10)
    wheel.select_index(30)
    wheel.leave_folder()
    choose(wheel, 3, 10)
    assert wheel.wheel()["selected"] == 30


def test_the_search_survives_leaving_song_select(wheel):
    """Coming back inside the folder has to find it filled again.

    The filter lives on SongSelect rather than in the folder, so without
    putting it back the restored path opens an empty folder.
    """
    choose(wheel, 3, 10)
    wheel.page.evaluate("() => __ss.rememberPlace()")
    wheel.page.evaluate("() => { __ss.clean(); window.__ss = new SongSelect(false, false, false) }")
    wheel.page.wait_for_function("() => __ss.songs && __ss.songs.length", timeout=20000)
    restored = wheel.page.evaluate("""() => {
        const index = __ss.restorePlace()
        return {index: index, path: __ss.navigator.pathIds(),
                songs: __ss.songs.filter(s => !s.action).length}
    }""")
    assert restored["path"] == ["collection:diffsort"]
    assert restored["songs"] > 0, "came back into an empty folder"


# -------------------------------------------------------------- the mouse


def test_clicking_a_course_moves_to_it_and_clicking_again_opens_it(wheel):
    """One click to move, a second to go on -- as the wheel below does."""
    open_picker(wheel)
    # the third difficulty box, at its own top-left plus a little
    wheel.page.evaluate("""() => {
        const P = DiffSortSelect.pos
        __ss.diffSortMouse(P.box.x + 2 * DiffSortSelect.boxOffset + 40, P.box.y + 100)
    }""")
    assert picker(wheel)["box"] == 2
    assert picker(wheel)["levelSelect"] is False, "opened it on the first click"
    wheel.page.evaluate("""() => {
        const P = DiffSortSelect.pos
        __ss.diffSortMouse(P.box.x + 2 * DiffSortSelect.boxOffset + 40, P.box.y + 100)
    }""")
    assert picker(wheel)["levelSelect"] is True


def test_the_arrows_step_the_level(wheel):
    open_picker(wheel)
    press(wheel, "right", 4)
    press(wheel, "select")
    press(wheel, "right", 3)
    assert picker(wheel)["level"] == 4
    wheel.page.evaluate("""() => {
        const a = DiffSortSelect.pos.arrow[0]
        __ss.diffSortMouse(a.x + 35, a.y + 35)
    }""")
    assert picker(wheel)["level"] == 3
    wheel.page.evaluate("""() => {
        const a = DiffSortSelect.pos.arrow[1]
        __ss.diffSortMouse(a.x + 35, a.y + 35)
    }""")
    assert picker(wheel)["level"] == 4


def test_clicking_away_from_the_panel_backs_out(wheel):
    open_picker(wheel)
    wheel.page.evaluate("() => __ss.diffSortMouse(5, 700)")
    assert picker(wheel) is None
    assert wheel.path() == []


def test_clicking_the_way_out_backs_out(wheel):
    open_picker(wheel)
    wheel.page.evaluate("""() => {
        const P = DiffSortSelect.pos
        __ss.diffSortMouse(P.back.x + 40, P.back.y + 160)
    }""")
    # already on the back box, so the click is the confirm
    assert picker(wheel) is None
    assert wheel.path() == []


# ------------------------------------------------------------ the drawing


def test_it_draws_without_error_on_every_screen(wheel):
    """The art is absent from the public build; it must still not throw."""
    open_picker(wheel)
    wheel.page.wait_for_timeout(200)
    press(wheel, "right", 4)
    wheel.page.wait_for_timeout(200)
    press(wheel, "select")
    wheel.page.wait_for_timeout(200)
    press(wheel, "select")
    wheel.page.wait_for_timeout(400)
    assert wheel.errors == []


# ------------------------------------------------------------- the crowns


def test_the_counts_are_cumulative(wheel):
    """A full combo is a clear, and a donderful is both.

    The panel shows three rows and each is a subset of the one above it,
    so a chart you full comboed is counted in the clears too. Seeded
    rather than read, because a fresh profile has no crowns at all and
    three zeroes would pass anything.
    """
    seeded = wheel.page.evaluate("""() => {
        const songs = assets.songs.filter(s => s.courses.oni && s.courses.oni.stars === 10)
        const n = {silver: 0, gold: 0, rainbow: 0}
        songs.forEach((s, i) => {
            const kind = i % 7 === 0 ? "rainbow" : i % 3 === 0 ? "gold"
                       : i % 2 === 0 ? "silver" : null
            if(!kind) return
            n[kind]++
            scoreStorage.scores[s.hash] = Object.assign(
                scoreStorage.scores[s.hash] || {}, {oni: {crown: kind}})
        })
        return n
    }""")
    assert seeded["rainbow"] > 0 and seeded["gold"] > 0 and seeded["silver"] > 0

    cell = wheel.page.evaluate("""() => {
        const c = __ss.navigator.diffSortStats()[3][10]
        return {total: c.total, clears: c.clears,
                fullCombos: c.fullCombos, donderfuls: c.donderfuls}
    }""")
    assert cell["donderfuls"] == seeded["rainbow"]
    assert cell["fullCombos"] == seeded["gold"] + seeded["rainbow"]
    assert cell["clears"] == seeded["silver"] + seeded["gold"] + seeded["rainbow"]
    assert cell["clears"] >= cell["fullCombos"] >= cell["donderfuls"]
    assert cell["clears"] <= cell["total"]


def test_a_courses_totals_carry_the_donderfuls_too(wheel):
    """The summed-over-levels view the difficulty boxes stand on."""
    wheel.page.evaluate("""() => {
        assets.songs.filter(s => s.courses.oni).slice(0, 30).forEach(s => {
            scoreStorage.scores[s.hash] = Object.assign(
                scoreStorage.scores[s.hash] || {}, {oni: {crown: "rainbow"}})
        })
    }""")
    open_picker(wheel)
    press(wheel, "right", 4)
    sums = wheel.page.evaluate("""() => {
        const p = __ss.diffSortSelect
        const course = p.courseStats[3]
        const rolled = p.stats[3].reduce((a, c) => ({
            clears: a.clears + c.clears,
            fullCombos: a.fullCombos + c.fullCombos,
            donderfuls: a.donderfuls + c.donderfuls
        }), {clears: 0, fullCombos: 0, donderfuls: 0})
        return {course: {clears: course.clears, fullCombos: course.fullCombos,
                         donderfuls: course.donderfuls}, rolled: rolled}
    }""")
    assert sums["course"]["donderfuls"] > 0, "the seeded donderfuls did not reach the panel"
    assert sums["course"] == sums["rolled"]


def test_the_panel_draws_three_crown_rows(wheel):
    """Three rows where the skin's artwork has two, so they are laid out
    here -- and they have to stay inside the panel's frame."""
    box = wheel.page.evaluate("""() => {
        const P = DiffSortSelect.panel
        return {lastRowBottom: P.rowTop + 2 * P.rowPitch + P.rowPitch,
                countRight: P.countRight, overRight: P.overRight,
                panelRight: DiffSortSelect.panelRight}
    }""")
    # the panel's frame is drawn to y 427 and x 252
    assert box["lastRowBottom"] <= 427, "the third row hangs out of the panel"
    assert box["overRight"] <= box["panelRight"], "the totals run past the frame"
    assert box["countRight"] < box["overRight"]
