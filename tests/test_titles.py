"""The title above the name on the nameplate.

There is a slot above the name that upstream only ever filled with "Not
logged in". A title is a line a player writes for themselves, so it has
to survive the trip out to the server and back, and it has to reach the
plate -- which is drawn from a cache keyed on what is written on it, so a
title that changes nothing in that key is a title nobody ever sees.
"""

import pytest

from conftest import Game


def post(page, url, body):
    return page.evaluate("""async ([url, body]) => {
        const csrf = await fetch("/api/csrftoken").then(r => r.json())
        return fetch(url, {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrf.token},
            body: JSON.stringify(body),
        }).then(r => r.json())
    }""", [url, body])


@pytest.fixture
def signed_in(game):
    """A registered account, signed in, with no title yet."""
    name = "titleboxtest"
    res = post(game.page, "/api/register", {"username": name, "password": "titleboxpass"})
    if res["status"] != "ok":
        res = post(game.page, "/api/login", {"username": name, "password": "titleboxpass"})
    assert res["status"] == "ok", f"could not sign in: {res}"
    post(game.page, "/api/account/title", {"title": ""})
    game.load()
    game.page.wait_for_function("() => account.loggedIn === true", timeout=10000)
    return game


def test_the_server_keeps_a_title(signed_in):
    saved = post(signed_in.page, "/api/account/title", {"title": "Master of Wada"})
    assert saved == {"status": "ok", "title": "Master of Wada"}

    signed_in.load()
    signed_in.page.wait_for_function("() => account.loggedIn === true", timeout=10000)
    assert signed_in.page.evaluate("() => account.title") == "Master of Wada"


def test_a_title_is_allowed_to_be_nothing(signed_in):
    post(signed_in.page, "/api/account/title", {"title": "Master of Wada"})
    assert post(signed_in.page, "/api/account/title", {"title": ""})["title"] == ""

    signed_in.load()
    signed_in.page.wait_for_function("() => account.loggedIn === true", timeout=10000)
    assert signed_in.page.evaluate("() => account.title") == ""


def test_an_overlong_title_is_refused(signed_in):
    # Turned away by the schema before the route sees it, the same as an
    # overlong display name, so this comes back as a plain 400.
    code = signed_in.page.evaluate("""async () => {
        const csrf = await fetch("/api/csrftoken").then(r => r.json())
        const r = await fetch("/api/account/title", {
            method: "POST",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrf.token},
            body: JSON.stringify({title: "x".repeat(26)}),
        })
        return r.status
    }""")
    assert code == 400


def test_the_box_sits_under_the_name_box(signed_in):
    post(signed_in.page, "/api/account/title", {"title": "Master of Wada"})
    signed_in.load()
    signed_in.page.wait_for_function("() => account.loggedIn === true", timeout=10000)
    signed_in.page.evaluate("() => new Account(false)")
    signed_in.page.wait_for_selector(".account-title", timeout=15000)

    shown = signed_in.page.evaluate("""() => {
        const name = document.querySelector(".displayname")
        const title = document.querySelector(".account-title")
        return {
            value: title.value,
            hint: document.querySelector(".title-hint").innerText,
            // 2 means the title box follows the name box in the document
            after: name.compareDocumentPosition(title) & 4 ? true : false,
        }
    }""")
    assert shown["value"] == "Master of Wada"
    assert shown["hint"]
    assert shown["after"], "the title box should come after the name box"


def test_the_plate_redraws_when_the_title_changes(signed_in):
    """The nameplate is cached, and the cache is keyed on what it says."""
    post(signed_in.page, "/api/account/title", {"title": "Master of Wada"})
    signed_in.load().open_song_select()
    signed_in.page.wait_for_function("() => account.loggedIn === true", timeout=10000)

    ids = signed_in.page.evaluate("""() => {
        const seen = []
        const cache = __ss.nameplateCache
        const real = cache.get.bind(cache)
        cache.get = (config, callback) => {
            seen.push(config.id)
            return real(config, callback)
        }
        __ss.draw.nameplate = () => {}
        __ss.redraw()
        const before = seen.slice()
        account.title = "Bachi Breaker"
        seen.length = 0
        __ss.redraw()
        return {before: before, after: seen.slice()}
    }""")
    assert any("Master of Wada" in i for i in ids["before"]), ids["before"]
    assert any("Bachi Breaker" in i for i in ids["after"]), ids["after"]
