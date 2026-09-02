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
