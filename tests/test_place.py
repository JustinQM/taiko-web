"""Coming back to where you were.

Finishing a song rebuilds song select from scratch. The remembered
position is an index, which means nothing on its own once the wheel is a
tree -- it is a position in whichever listing was open. So the folder
goes with it.
"""

import pytest


@pytest.fixture
def wheel(game):
    return game.open_song_select()


def remembered(wheel):
    return wheel.page.evaluate("""() => ({
        index: localStorage["selectedSong"],
        path: localStorage["selectedPath"],
    })""")


def test_the_folder_is_remembered_with_the_index(wheel):
    wheel.enter_folder()
    wheel.select_index(12)
    wheel.page.evaluate("() => __ss.rememberPlace()")
    stored = remembered(wheel)
    assert stored["index"] == "12"
    assert stored["path"] == '["genre:Pop"]'


def test_reopening_lands_on_the_same_song_in_the_same_folder(wheel):
    wheel.enter_folder()
    wheel.select_index(12)
    title = wheel.wheel()["title"]
    wheel.page.evaluate("() => __ss.rememberPlace()")

    wheel.load().open_song_select()
    state = wheel.wheel()
    assert wheel.path() == ["genre:Pop"], f"came back to {wheel.path()}"
    assert state["selected"] == 12
    assert state["title"] == title


def test_the_root_still_works(wheel):
    wheel.select_index(3)
    wheel.page.evaluate("() => __ss.rememberPlace()")
    wheel.load().open_song_select()
    assert wheel.path() == []
    assert wheel.wheel()["selected"] == 3


def test_a_folder_that_has_gone_falls_back_to_the_root(wheel):
    """A genre emptied or a favorite removed must not strand the wheel
    part way down a path that no longer exists."""
    wheel.page.evaluate("""() => {
        localStorage["selectedPath"] = JSON.stringify(["genre:NoSuchThing"])
        localStorage["selectedSong"] = "5"
    }""")
    wheel.load().open_song_select()
    assert wheel.path() == []
    assert wheel.errors == []


def test_a_stale_index_is_clamped(wheel):
    """The folder may still exist but be shorter than it was."""
    wheel.page.evaluate("""() => {
        localStorage["selectedPath"] = JSON.stringify(["genre:Pop"])
        localStorage["selectedSong"] = "999999"
    }""")
    wheel.load().open_song_select()
    state = wheel.wheel()
    assert state["selected"] < wheel.page.evaluate("() => __ss.songs.length")
    assert wheel.errors == []


def test_nonsense_in_storage_is_ignored(wheel):
    wheel.page.evaluate("""() => { localStorage["selectedPath"] = "{not json" }""")
    wheel.load().open_song_select()
    assert wheel.path() == []
    assert wheel.errors == []
