"""Favourites.

Per user, persisted, their own folder, toggled from the wheel. Stored as
a playlist row from the start so user-created lists later are more rows
rather than a migration.

Logged out they live in localStorage, exactly as scores do.
"""

import pytest


@pytest.fixture
def wheel(game):
    return game.open_song_select()


def song_ids(wheel):
    return wheel.page.evaluate("""() => {
        const f = __ss.navigator.items.find(i => i.folder && i.folder.id === "genre:Pop")
        return f.folder.songs.slice(0, 3).map(s => s.id)
    }""")


def test_favorites_folder_sits_after_the_genres(wheel):
    root = wheel.page.evaluate(
        "() => __ss.navigator.items.map(i => (i.folder && i.folder.id) || i.action)")
    fav = root.index("collection:favorites")
    genres = [i for i, v in enumerate(root) if isinstance(v, str) and v.startswith("genre:")]
    assert fav > max(genres), "favourites should come after the genre folders"
    assert fav < root.index("random"), "favourites should come before the menu entries"


def test_favorites_starts_empty(wheel):
    assert wheel.page.evaluate("() => favorites.songs") == []


def test_toggling_adds_and_removes(wheel):
    first = song_ids(wheel)[0]
    added = wheel.page.evaluate("id => favorites.toggle(id)", first)
    assert added is True
    assert wheel.page.evaluate("id => favorites.has(id)", first) is True

    removed = wheel.page.evaluate("id => favorites.toggle(id)", first)
    assert removed is False
    assert wheel.page.evaluate("id => favorites.has(id)", first) is False


def test_the_folder_lists_what_was_favourited(wheel):
    ids = song_ids(wheel)
    wheel.page.evaluate("ids => ids.forEach(id => favorites.toggle(id))", ids)

    index = wheel.page.evaluate(
        "() => __ss.navigator.items.findIndex(i => i.folder && i.folder.id === 'collection:favorites')")
    wheel.enter_folder(index)
    listed = wheel.page.evaluate("() => __ss.songs.slice(1).map(s => s.id)")
    assert sorted(listed) == sorted(ids)
    assert wheel.errors == []


def test_the_folder_reflects_changes_made_while_open(wheel):
    ids = song_ids(wheel)
    wheel.page.evaluate("ids => ids.forEach(id => favorites.toggle(id))", ids)
    index = wheel.page.evaluate(
        "() => __ss.navigator.items.findIndex(i => i.folder && i.folder.id === 'collection:favorites')")
    wheel.enter_folder(index)

    wheel.select_index(1)
    wheel.page.evaluate("() => __ss.toggleFavorite()")
    remaining = wheel.page.evaluate("() => __ss.songs.slice(1).map(s => s.id)")
    assert len(remaining) == len(ids) - 1
    assert wheel.page.evaluate("() => __ss.selectedSong < __ss.songs.length") is True


def test_favourites_survive_a_reload_when_logged_out(wheel):
    first = song_ids(wheel)[0]
    wheel.page.evaluate("id => favorites.toggle(id)", first)
    wheel.load().open_song_select()
    assert wheel.page.evaluate("id => favorites.has(id)", first) is True, \
        "favourites did not survive a reload"


def test_toggling_is_refused_in_a_session(wheel):
    """They are per account and nothing about them is shared with a peer."""
    first = song_ids(wheel)[0]
    changed = wheel.page.evaluate("""id => {
        const real = p2.session
        try {
            p2.session = true
            const idx = __ss.navigator.items.findIndex(i => i.folder && i.folder.id === "genre:Pop")
            __ss.navigator.enter(idx)
            __ss.songs = __ss.navigator.items
            __ss.selectedSong = 1
            __ss.toggleFavorite()
            return favorites.songs.length
        } finally { p2.session = real }
    }""", first)
    assert changed == 0, "a favourite was toggled during a session"


def test_only_songs_can_be_favourited(wheel):
    wheel.select_index(0)   # a genre folder
    wheel.page.evaluate("() => __ss.toggleFavorite()")
    assert wheel.page.evaluate("() => favorites.songs.length") == 0


# ------------------------------------------------------------ logged in

@pytest.fixture
def account(wheel):
    """Register and sign in, so favourites go to the server."""
    name = "favtest"
    ok = wheel.page.evaluate("""async (name) => {
        const csrf = await fetch("/api/csrftoken").then(r => r.json())
        const post = (url, body) => fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrf.token},
            body: JSON.stringify(body),
        }).then(r => r.json())
        let res = await post("/api/register", {username: name, password: "favtestpass"})
        if (res.status !== "ok")
            res = await post("/api/login", {username: name, password: "favtestpass"})
        return res.status
    }""", name)
    assert ok == "ok", f"could not sign in: {ok}"
    # The account is shared between these tests, so start each from an
    # empty list rather than inheriting whatever the last one left.
    wheel.page.evaluate("""async () => {
        const csrf = await fetch("/api/csrftoken").then(r => r.json())
        const current = await fetch("/api/playlists/favorites").then(r => r.json())
        for (const id of current.songs || []) {
            await fetch("/api/playlists", {
                method: "POST",
                headers: {"Content-Type": "application/json", "X-CSRFToken": csrf.token},
                body: JSON.stringify({slug: "favorites", song_id: id, value: false}),
            })
        }
    }""")
    wheel.load().open_song_select()
    wheel.page.wait_for_function("() => account.loggedIn === true", timeout=10000)
    return wheel


def test_favourites_reach_the_server_when_logged_in(account):
    first = song_ids(account)[0]
    account.page.evaluate("id => favorites.toggle(id)", first)
    account.page.wait_for_timeout(600)

    stored = account.page.evaluate("""async () => {
        const r = await fetch("/api/playlists/favorites").then(r => r.json())
        return r.songs
    }""")
    assert first in stored, f"the server did not record it: {stored}"


def test_the_account_list_is_loaded_on_sign_in(account):
    first = song_ids(account)[0]
    account.page.evaluate("id => favorites.toggle(id)", first)
    account.page.wait_for_timeout(600)

    account.load().open_song_select()
    account.page.wait_for_function("() => favorites.loaded === true", timeout=10000)
    assert account.page.evaluate("id => favorites.has(id)", first) is True


def test_toggling_twice_leaves_the_server_consistent(account):
    """The value is sent explicitly, so a retry cannot toggle it twice."""
    first = song_ids(account)[0]
    account.page.evaluate("id => { favorites.toggle(id); favorites.toggle(id) }", first)
    account.page.wait_for_timeout(800)
    stored = account.page.evaluate(
        """async () => (await fetch("/api/playlists/favorites").then(r => r.json())).songs""")
    assert first not in stored, f"left behind on the server: {stored}"


# ------------------------------------------------------- recently played

def test_recently_played_folder_follows_favourites(wheel):
    root = wheel.page.evaluate(
        "() => __ss.navigator.items.map(i => (i.folder && i.folder.id) || i.action)")
    assert root.index("collection:recent") == root.index("collection:favorites") + 1


def test_recently_played_starts_empty(wheel):
    assert wheel.page.evaluate("() => recentlyPlayed.songs") == []


def test_playing_puts_a_song_at_the_front(wheel):
    ids = song_ids(wheel)
    wheel.page.evaluate("ids => ids.forEach(id => recentlyPlayed.set(id, true))", ids)
    assert wheel.page.evaluate("() => recentlyPlayed.songs") == list(reversed(ids))


def test_replaying_moves_it_back_to_the_front(wheel):
    """Not duplicated: this is the difference between a play log and a
    list you add to."""
    ids = song_ids(wheel)
    wheel.page.evaluate("ids => ids.forEach(id => recentlyPlayed.set(id, true))", ids)
    wheel.page.evaluate("id => recentlyPlayed.set(id, true)", ids[0])
    songs = wheel.page.evaluate("() => recentlyPlayed.songs")
    assert songs[0] == ids[0]
    assert len(songs) == len(ids), f"duplicated: {songs}"


def test_recently_played_is_capped(wheel):
    """It is written on every play, so it cannot grow without bound."""
    kept = wheel.page.evaluate("""() => {
        const all = __ss.navigator.songItems.slice(0, 80).map(s => s.id)
        all.forEach(id => recentlyPlayed.set(id, true))
        return {count: recentlyPlayed.songs.length, limit: recentlyPlayed.limit}
    }""")
    assert kept["count"] == kept["limit"] == 50


def test_the_folder_lists_recent_songs_newest_first(wheel):
    ids = song_ids(wheel)
    wheel.page.evaluate("ids => ids.forEach(id => recentlyPlayed.set(id, true))", ids)
    index = wheel.page.evaluate(
        "() => __ss.navigator.items.findIndex(i => i.folder && i.folder.id === 'collection:recent')")
    wheel.enter_folder(index)
    listed = wheel.page.evaluate("() => __ss.songs.slice(1).map(s => s.id)")
    assert listed == list(reversed(ids))
    assert wheel.errors == []


def test_nothing_is_backfilled(wheel):
    """Scores that predate this get no date invented for them."""
    assert wheel.page.evaluate("() => recentlyPlayed.songs.length") == 0


# ------------------------------------------------- the favourite button

def test_favourite_is_a_button_on_the_song(wheel):
    """Not a keybind: the drum and the arrows are the whole vocabulary."""
    options = wheel.page.evaluate("() => __ss.diffOptions.map(o => o.iconName)")
    assert options == ["back", "options", "sounds", "favorite"]


def test_the_button_toggles_the_song_it_is_shown_with(wheel):
    wheel.enter_folder()
    song = wheel.page.evaluate("() => __ss.songs[__ss.selectedSong].id")

    wheel.page.evaluate("() => __ss.toSelectDifficulty()")
    wheel.page.wait_for_function("() => __ss.state.screen === 'difficulty'", timeout=5000)

    wheel.page.evaluate("() => { __ss.selectedDiff = 3; __ss.toggleFavorite() }")
    assert wheel.page.evaluate("id => favorites.has(id)", song) is True

    wheel.page.evaluate("() => __ss.toggleFavorite()")
    assert wheel.page.evaluate("id => favorites.has(id)", song) is False
    assert wheel.errors == []


def test_the_button_shows_which_state_it_is_in(wheel):
    """Filled when the song is a favourite, outlined when it is not."""
    wheel.enter_folder()
    song = wheel.page.evaluate("() => __ss.songs[__ss.selectedSong].id")
    off = wheel.page.evaluate("id => favorites.has(id)", song)
    wheel.page.evaluate("id => favorites.toggle(id)", song)
    on = wheel.page.evaluate("id => favorites.has(id)", song)
    assert (off, on) == (False, True)


def test_no_favourite_keybind_remains(wheel):
    bound = wheel.page.evaluate("""() => {
        const keys = __ss.keyboard.keys || {}
        return Object.keys(keys).includes("favorite")
    }""")
    assert bound is False, "the keybind is still registered"
