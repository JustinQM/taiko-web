"""Two clients in a real netplay session.

Netplay has broken twice in this work, both times because something was
checked in isolation and looked right. A selection only means anything as
an index into a listing, so the two clients have to be watched together,
against the real multiplayer server, doing the thing a player would do.
"""

import pytest

from conftest import TAIKO_URL, Game


def open_client(context):
    page = context.new_page()
    game = Game(page)
    game.load().open_song_select()
    return game


@pytest.fixture
def pair(browser):
    """Two clients in a session with each other."""
    context_a = browser.new_context()
    context_b = browser.new_context()
    a = open_client(context_a)
    b = open_client(context_b)

    a.page.wait_for_function("() => p2.socket && p2.socket.readyState === 1", timeout=15000)
    b.page.wait_for_function("() => p2.socket && p2.socket.readyState === 1", timeout=15000)

    # The invite code comes back as a message rather than being stored,
    # so listen for it before asking for one.
    #
    # Registered on p2 directly rather than through pageEvents.add, which
    # removes any existing listener for the same target and type before
    # adding -- it would silently evict SongSelect's own handler and the
    # client would stop responding to its peer entirely. p2 keeps its
    # listeners in a Set, so adding to it directly disturbs nothing.
    a.page.evaluate("""() => {
        window.__invite = null
        p2.addEventListener("message", r => {
            if(r.type === "invite") window.__invite = r.value
        })
        // the server wants an explicit null id to mean "give me a code"
        p2.send("invite", {id: null})
    }""")
    a.page.wait_for_function("() => window.__invite", timeout=15000)
    invite = a.page.evaluate("() => window.__invite")
    b.page.evaluate("id => p2.send('invite', {id: id})", invite)

    for client in (a, b):
        client.page.wait_for_function("() => p2.session === true", timeout=15000)

    # A bare songsel is what moves both sides from the session screen into
    # song select; the server only relays selections once they are there.
    a.page.evaluate("() => p2.send('songsel')")
    a.page.wait_for_timeout(500)

    yield a, b

    context_a.close()
    context_b.close()


def settled(client, expected_path, timeout=8000):
    client.page.wait_for_function(
        "ids => JSON.stringify(__ss.navigator.pathIds()) === JSON.stringify(ids)",
        arg=expected_path, timeout=timeout)


def test_a_session_starts(pair):
    a, b = pair
    assert a.page.evaluate("() => p2.session") is True
    assert b.page.evaluate("() => p2.session") is True
    assert a.path() == [] and b.path() == []


def test_descending_takes_the_peer_with_you(pair):
    a, b = pair
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")

    settled(a, ["genre:Pop"])
    settled(b, ["genre:Pop"])
    assert a.path() == b.path() == ["genre:Pop"]


def test_the_peer_lands_on_the_same_song(pair):
    a, b = pair
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")
    settled(a, ["genre:Pop"])
    settled(b, ["genre:Pop"])

    a.page.evaluate("() => __ss.moveToSong(3)")
    a.settle()
    b.page.wait_for_function(
        "() => __ss.state.locked === 0 && __ss.selectedSong !== 0", timeout=8000)

    assert a.wheel()["title"] == b.wheel()["title"], "the two are on different songs"


def test_coming_back_out_takes_the_peer_too(pair):
    a, b = pair
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")
    settled(a, ["genre:Pop"])
    settled(b, ["genre:Pop"])

    # the back box is the first entry of a folder listing
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")
    settled(a, [])
    settled(b, [])
    assert a.path() == b.path() == []


def test_either_side_can_lead(pair):
    """Both clients drive the same protocol; neither is the host."""
    a, b = pair
    b.page.evaluate("() => { __ss.selectedSong = 1; __ss.toSelectDifficulty() }")
    settled(b, ["genre:Anime"])
    settled(a, ["genre:Anime"])
    assert a.path() == b.path() == ["genre:Anime"]


def test_a_selection_still_syncs_at_the_root(pair):
    """The root is a listing like any other and must not be special."""
    a, b = pair
    start = a.wheel()["selected"]
    a.page.evaluate("() => __ss.moveToSong(2)")
    a.settle()
    b.page.wait_for_function(
        "from => __ss.selectedSong !== from", arg=start, timeout=8000)
    b.settle()
    assert a.wheel()["selected"] == b.wheel()["selected"]
    assert a.wheel()["title"] == b.wheel()["title"]


def test_the_socket_reconnects_after_the_server_restarts(browser):
    """p2 registered its close listener through pageEvents.race, which
    removes both listeners as soon as either fires -- so once a connection
    succeeded the close listener was gone, a later disconnect was never
    noticed, and the retry inside closeEvent was unreachable in the case
    it was written for.
    """
    import subprocess

    context = browser.new_context()
    client = open_client(context)
    client.page.wait_for_function(
        "() => p2.socket && p2.socket.readyState === 1", timeout=15000)

    subprocess.run(
        ["sg", "docker", "-c", "docker restart taiko-web-multiplayer-1"],
        check=True, capture_output=True)

    # It must notice the socket has gone...
    client.page.wait_for_function(
        "() => !p2.socket || p2.socket.readyState !== 1", timeout=20000)
    # ...and come back on its own, without anything asking it to.
    client.page.wait_for_function(
        "() => p2.socket && p2.socket.readyState === 1", timeout=45000)

    context.close()


def test_the_socket_closes_when_the_page_goes_away(pair):
    """Nothing closed it on unload, so a refresh left the server holding
    the connection and the waiting list filling with ghosts."""
    a, b = pair
    closed = a.page.evaluate("""() => {
        let closedCalled = false
        const real = p2.close.bind(p2)
        p2.close = () => { closedCalled = true; return real() }
        window.dispatchEvent(new Event("beforeunload"))
        return closedCalled
    }""")
    assert closed is True, "beforeunload did not close the socket"


def wheel_state(client):
    return client.page.evaluate("""() => ({
        path: __ss.navigator.pathIds(),
        title: __ss.songs[__ss.selectedSong].title,
        action: __ss.songs[__ss.selectedSong].action || null
    })""")


def agree(a, b, timeout=8000):
    """Wait until both clients report the same place, then return it."""
    a.page.wait_for_function("() => __ss.state.locked === 0", timeout=timeout)
    b.page.wait_for_function("() => __ss.state.locked === 0", timeout=timeout)
    for _ in range(40):
        first, second = wheel_state(a), wheel_state(b)
        if first == second:
            return first
        a.page.wait_for_timeout(200)
    raise AssertionError(f"never agreed: {wheel_state(a)} vs {wheel_state(b)}")


def test_random_takes_the_peer_with_you(pair):
    """Random rolled locally and told the peer nothing, so one client
    went off to a song and the other stayed standing on Random.

    Only one side may roll -- rolling separately would send them to two
    different songs -- so the song travels with the message and both act
    on the echo, the way opening a folder does."""
    a, b = pair
    index = a.page.evaluate(
        "() => __ss.songs.findIndex(s => s.action === 'random')")
    assert index >= 0, "no Random entry at the root"

    a.page.evaluate("i => { __ss.selectedSong = i; __ss.toSelectDifficulty() }", index)
    where = agree(a, b, timeout=15000)
    assert where["action"] is None, f"still standing on a menu entry: {where}"
    assert where["path"], "random landed outside any folder"


def test_a_run_of_moves_all_arrive(pair):
    """Sending was gated to one move per 800ms on top of the flag that
    already keeps one in flight, so at any normal scrolling pace four
    presses out of five went nowhere -- which is what made netplay
    navigation feel like it was not tracking."""
    a, b = pair
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")
    settled(a, ["genre:Pop"])
    settled(b, ["genre:Pop"])
    start = a.page.evaluate("() => __ss.selectedSong")

    for _ in range(5):
        a.page.evaluate("() => __ss.moveToSong(1)")
        a.page.wait_for_timeout(250)

    where = agree(a, b)
    moved = a.page.evaluate("() => __ss.selectedSong") - start
    assert moved >= 4, f"only {moved} of 5 presses moved the wheel"
    assert where["path"] == ["genre:Pop"]


def test_two_quick_moves_from_the_peer_are_not_read_as_a_jump(pair):
    """A double-press here means 'jump ten'. A move from the peer is an
    index it has already committed to, and two of them arriving close
    together must not be multiplied -- that lands the two clients ten
    songs apart."""
    a, b = pair
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")
    settled(a, ["genre:Pop"])
    settled(b, ["genre:Pop"])
    start = a.page.evaluate("() => __ss.selectedSong")

    a.page.evaluate("() => __ss.moveToSong(1)")
    a.page.wait_for_timeout(120)
    a.page.evaluate("() => __ss.moveToSong(1)")

    agree(a, b)
    assert a.page.evaluate("() => __ss.selectedSong") - start <= 2


def test_a_category_jump_syncs(pair):
    """At the root a jump steps between genres and is sent as its own
    message; inside a folder it becomes a page of ten."""
    a, b = pair
    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.categoryJump(1) }")
    root = agree(a, b)
    assert root["path"] == []

    a.page.evaluate("() => { __ss.selectedSong = 0; __ss.toSelectDifficulty() }")
    inside = agree(a, b)
    assert inside["path"], "did not descend"

    before = a.page.evaluate("() => __ss.selectedSong")
    a.page.evaluate("() => __ss.categoryJump(1)")
    agree(a, b)
    assert a.page.evaluate("() => __ss.selectedSong") != before


def test_a_lost_reply_does_not_lock_the_wheel(pair):
    """Every move waits for its echo. A flag that only a reply clears is
    a flag a lost reply leaves set for good."""
    a, b = pair
    stuck = a.page.evaluate("""() => {
        __ss.lockSend()
        const immediately = __ss.sendLocked()
        __ss.state.selLockMS = __ss.getMS() - 2000
        return [immediately, __ss.sendLocked()]
    }""")
    assert stuck == [True, False]


def test_search_takes_the_peer_with_you(pair):
    """Search picks out of a list the peer never saw, so the song it
    landed on has to travel with the message -- the same way random does.
    Both clients open its folder and its difficulty screen."""
    a, b = pair
    wanted = a.page.evaluate("""() => {
        const song = __ss.navigator.songItems[200] || __ss.navigator.songItems[0]
        __ss.searchProceed(song.id)
        return song.title
    }""")
    for client in (a, b):
        client.page.wait_for_function(
            "() => __ss.state.screen === 'difficulty'", timeout=15000)
    assert a.wheel()["title"] == wanted
    assert b.wheel()["title"] == wanted
    assert a.path() == b.path()


def sign_in_with_title(game, name, title):
    """A registered account carrying a title, ready to play."""
    ok = game.page.evaluate("""async ([name, title]) => {
        const csrf = await fetch("/api/csrftoken").then(r => r.json())
        const post = (url, body) => fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrf.token},
            body: JSON.stringify(body),
        }).then(r => r.json())
        let res = await post("/api/register", {username: name, password: "titletestpass"})
        if (res.status !== "ok")
            res = await post("/api/login", {username: name, password: "titletestpass"})
        if (res.status !== "ok") return res.status
        return (await post("/api/account/title", {title: title})).status
    }""", [name, title])
    assert ok == "ok", f"could not sign in: {ok}"
    game.load().open_song_select()
    game.page.wait_for_function("() => account.loggedIn === true", timeout=10000)
    return game


def test_a_title_reaches_the_other_player(browser):
    """Both sides see the other's title, not just their name.

    The title rides along with the name through the handshake, and the
    handshake is the only place it is sent -- a plate drawn before it
    arrives, or a server that drops the field, shows the name alone and
    looks like nothing is wrong.
    """
    context_a = browser.new_context()
    context_b = browser.new_context()
    a = sign_in_with_title(open_client(context_a), "titletest1", "Master of Wada")
    b = sign_in_with_title(open_client(context_b), "titletest2", "Bachi Breaker")

    for client in (a, b):
        client.page.wait_for_function(
            "() => p2.socket && p2.socket.readyState === 1", timeout=15000)

    a.page.evaluate("""() => {
        window.__invite = null
        p2.addEventListener("message", r => {
            if(r.type === "invite") window.__invite = r.value
        })
        p2.send("invite", {
            id: null, name: account.displayName, title: account.title, don: account.don
        })
    }""")
    a.page.wait_for_function("() => window.__invite", timeout=15000)
    invite = a.page.evaluate("() => window.__invite")
    b.page.evaluate("""id => p2.send("invite", {
        id: id, name: account.displayName, title: account.title, don: account.don
    })""", invite)

    for client in (a, b):
        client.page.wait_for_function("() => p2.session === true", timeout=15000)
        client.page.wait_for_function("() => p2.title", timeout=15000)

    assert a.page.evaluate("() => p2.title") == "Bachi Breaker"
    assert b.page.evaluate("() => p2.title") == "Master of Wada"

    context_a.close()
    context_b.close()


def test_a_missing_title_leaves_the_plate_as_it_was(pair):
    """Nobody has to have one, and no title must not read as one."""
    a, b = pair
    assert a.page.evaluate("() => p2.title") == ""
    assert b.page.evaluate("() => p2.title") == ""
