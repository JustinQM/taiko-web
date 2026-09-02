"""Scores drawn by the game rather than by a panel over it.

The service and its API are untouched; this is about where the scores are
shown. Everything degrades to an empty board: no service, no network, no
scores for that course.
"""

import pytest


@pytest.fixture
def wheel(game):
    return game.open_song_select()


def test_a_song_is_fetched_once(wheel):
    calls = wheel.page.evaluate("""async () => {
        let n = 0
        const real = highscores.fetch.bind(highscores)
        highscores.fetch = id => { n++; return real(id) }
        highscores.cache = {}
        highscores.pending = {}
        highscores.get(411); highscores.get(411); highscores.get(411)
        return n
    }""")
    assert calls == 1, f"asked the server {calls} times for one song"


def test_the_board_matches_the_api(wheel):
    result = wheel.page.evaluate("""async () => {
        highscores.cache = {}; highscores.pending = {}
        highscores.get(411)
        for (let i = 0; i < 60 && !(411 in highscores.cache); i++)
            await new Promise(r => setTimeout(r, 50))
        const api = await fetch("/highscores/api/song/411").then(r => r.json())
        const mine = highscores.board(411, "hard")
        return {
            apiRows: (api.boards.hard.rows || []).map(r => r.user + ":" + r.points),
            myRows: (mine ? mine.rows : []).map(r => r.user + ":" + r.points),
        }
    }""")
    assert result["myRows"] == result["apiRows"]


def test_a_failure_shows_an_empty_board_rather_than_retrying(wheel):
    """A song nobody can look up must not refetch on every frame."""
    calls = wheel.page.evaluate("""async () => {
        highscores.cache = {}; highscores.pending = {}
        let n = 0
        const realFetch = highscores.fetch.bind(highscores)
        highscores.fetch = id => { n++; highscores.cache[id] = null; delete highscores.pending[id] }
        for (let i = 0; i < 5; i++) highscores.board(999999, "oni")
        return {calls: n, board: highscores.board(999999, "oni")}
    }""")
    assert calls["calls"] == 1
    assert calls["board"] is None


def test_the_board_is_drawn_on_the_difficulty_screen(wheel):
    wheel.enter_folder()
    drew = wheel.page.evaluate("""() => {
        let filled = 0
        const ctx = {
            save(){}, restore(){}, fill(){ filled++ }, stroke(){}, beginPath(){},
            moveTo(){}, lineTo(){}, arcTo(){}, quadraticCurveTo(){}, closePath(){}, arc(){}, rect(){}, bezierCurveTo(){},
            fillText(){ filled++ }, measureText: () => ({width: 10}),
            translate(){}, scale(){},
            globalAlpha: 1, lineWidth: 1, font: "", fillStyle: "", strokeStyle: "",
            textAlign: "", textBaseline: "",
        }
        __ss.selectedSong = __ss.songs.findIndex(s => s.courses)
        __ss.selectedDiff = __ss.diffOptions.length + 2
        __ss.drawHighscores(ctx)
        return filled
    }""")
    assert drew > 0, "nothing was drawn"


def test_nothing_is_drawn_for_a_menu_entry(wheel):
    """The root has no songs, so there is nothing to show scores for."""
    drew = wheel.page.evaluate("""() => {
        let filled = 0
        const ctx = {save(){}, restore(){}, fill(){ filled++ }, fillText(){ filled++ }}
        __ss.selectedSong = __ss.songs.findIndex(s => s.action === "random")
        __ss.selectedDiff = __ss.diffOptions.length + 2
        __ss.drawHighscores(ctx)
        return filled
    }""")
    assert drew == 0


def test_it_follows_the_selected_course(wheel):
    """Which is the thing the website cannot do -- it shows every course
    at once, and this shows the one you are looking at."""
    wheel.enter_folder()
    asked = wheel.page.evaluate("""() => {
        const seen = []
        const real = highscores.board.bind(highscores)
        highscores.board = (id, diff) => { seen.push(diff); return real(id, diff) }
        const ctx = {save(){}, restore(){}, fill(){}, stroke(){}, beginPath(){},
            moveTo(){}, lineTo(){}, arcTo(){}, quadraticCurveTo(){}, closePath(){}, arc(){}, rect(){}, bezierCurveTo(){},
            fillText(){}, measureText: () => ({width: 10}), translate(){}, scale(){},
            globalAlpha: 1, lineWidth: 1, font: "", fillStyle: "", strokeStyle: "",
            textAlign: "", textBaseline: ""}
        __ss.selectedSong = __ss.songs.findIndex(s => s.courses)
        for (const d of [0, 2, 3]) {
            __ss.selectedDiff = __ss.diffOptions.length + d
            __ss.drawHighscores(ctx)
        }
        highscores.board = real
        return seen
    }""")
    assert asked == ["easy", "hard", "oni"], f"asked for {asked}"
