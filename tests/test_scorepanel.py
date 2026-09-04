"""The leaderboard panel on the results screen.

custom.js splices the run you just played into the board, because the
leaderboard's poller only sweeps once a minute and the API is usually
still serving the previous standings when a song ends.

Where that run is drawn is the whole point of it: it answers "where would
that have put me", which the board on its own cannot. It used to be
pinned directly beneath the player's own entry, so a run that beat
everything was drawn below the score it beat.

The board is stubbed rather than played for: reaching this panel for real
means finishing a song, and the cases worth testing are positions on a
board this stack does not happen to have.
"""

import pytest

BOARD = [
    {"rank": 1, "user": "alice", "points": 900000, "accuracy": 99.0, "crown": "gold",
     "good": 500, "ok": 5, "bad": 0, "maxCombo": 400},
    {"rank": 2, "user": "me", "points": 500000, "accuracy": 90.0, "crown": "silver",
     "good": 400, "ok": 50, "bad": 5, "maxCombo": 200},
    {"rank": 3, "user": "carol", "points": 300000, "accuracy": 80.0, "crown": "",
     "good": 300, "ok": 60, "bad": 20, "maxCombo": 100},
]

# selectedSong here is what song select hands the loader, not a song from
# the API: its "folder" is the song id under an older name. Inventing a
# shape for it is exactly what let a guard against a field that does not
# exist pass its tests and fail the game.
SETUP = """([board, points, players, signedIn]) => {
  window.__board = {boards: {oni: {label: "Oni", color: "#c8386e", stars: 9,
                                   players: players, rows: board}}}
  window.account = signedIn ? {loggedIn: true, username: "me"} : {loggedIn: false}
  if(!window.__realFetch) window.__realFetch = window.fetch
  window.__seen = []
  window.fetch = u => {
    window.__seen.push(String(u))
    return String(u).indexOf("/highscores/api/song/") !== -1
      ? Promise.resolve({ok: true, json: () => Promise.resolve(window.__board)})
      : window.__realFetch(u)
  }
  // the panel is hidden while a song is playing; the results have to
  // bring it back
  window.dispatchEvent(new CustomEvent("game-start"))
  window.dispatchEvent(new CustomEvent("scoresheet", {detail: {
    selectedSong: {folder: 1, title: "T", difficulty: "oni"},
    autoPlayEnabled: false, multiplayer: false,
    results: [{points: String(points), good: "450", ok: "20",
               bad: "2", maxCombo: "300"}]
  }}))
}"""

READ = """() => [...document.querySelectorAll("#hs .hs-d.hs-played .hs-row")]
  .map(r => ({
      rank: ((r.querySelector(".hs-rank") || {}).textContent || "").trim(),
      text: (r.querySelector(".hs-user") || {}).textContent.trim(),
      points: ((r.querySelector(".hs-pts") || {}).textContent || "").trim(),
      run: r.classList.contains("hs-cmp")
  }))"""


@pytest.fixture
def panel(game):
    game.page.wait_for_function("() => document.getElementById('hs')", timeout=40000)
    return game


def show(panel, points, board=None, players=3, signed_in=True):
    panel.page.evaluate(SETUP, [board if board is not None else BOARD,
                                points, players, signed_in])
    panel.page.wait_for_function(
        "() => document.querySelectorAll('#hs .hs-d.hs-played .hs-row').length > 0",
        timeout=8000)
    return panel.page.evaluate(READ)


def positions(rows):
    """The board top to bottom, with the run marked."""
    return [("RUN" if r["run"] else r["text"].split("\n")[0]) for r in rows]


def run_row(rows):
    return next(r for r in rows if r["run"])


# ------------------------------------------------------------ it shows at all


def test_the_run_is_shown(panel):
    rows = show(panel, 700000)
    assert any(r["run"] for r in rows), "the run just played is not on the panel"


def test_the_panel_comes_back_from_being_hidden(panel):
    """It is hidden for the whole song and the results event is what
    brings it back, so asking it to draw while it is already on screen
    proves nothing."""
    show(panel, 700000)
    assert panel.page.evaluate(
        "() => document.getElementById('hs').classList.contains('hidden')") is False


def test_a_guest_still_sees_where_the_run_would_have_gone(panel):
    """Without a name there is no row to match against, and the whole
    comparison used to be skipped with it -- so a signed-out player got
    the board and no sign of what they had just played."""
    rows = show(panel, 700000, signed_in=False)
    run = run_row(rows)
    assert positions(rows) == ["alice", "RUN", "me", "carol"]
    assert "NOT SIGNED IN" in run["text"].upper()
    # nothing to measure against, so nothing is claimed
    assert "+" not in run["text"] and "−" not in run["text"]
    assert "FIRST SCORE" not in run["text"].upper()


def test_it_fetches_the_board_for_the_song_id(panel):
    """The API route is /api/song/<int:song_id>, and the id is what the
    browsing half of this panel has always sent."""
    show(panel, 700000)
    urls = panel.page.evaluate("() => window.__seen || []")
    assert any("/highscores/api/song/1?" in u for u in urls), urls


# --------------------------------------------------------------- placement


def test_a_run_that_beats_everyone_goes_top(panel):
    rows = show(panel, 950000)
    assert positions(rows)[0] == "RUN"
    assert run_row(rows)["rank"] == "1"


def test_a_run_lands_between_the_scores_it_falls_between(panel):
    rows = show(panel, 700000)
    assert positions(rows) == ["alice", "RUN", "me", "carol"]


def test_a_run_worse_than_their_own_best_sits_where_it_belongs(panel):
    """Not under their entry -- at the place that worse score earns."""
    rows = show(panel, 400000)
    assert positions(rows) == ["alice", "me", "RUN", "carol"]


def test_a_run_worse_than_everything_goes_last(panel):
    rows = show(panel, 100000)
    assert positions(rows) == ["alice", "me", "carol", "RUN"]
    assert run_row(rows)["rank"] == "4"


def test_their_own_entry_stays_where_it_is(panel):
    """Both are worth seeing: the best they have, and where this went."""
    for points in (950000, 700000, 400000, 100000):
        rows = show(panel, points)
        assert "me" in positions(rows), points


# ------------------------------------------------------------- what it says


def test_the_delta_to_their_best_is_shown_either_way(panel):
    assert "+450,000" in run_row(show(panel, 950000))["text"]
    assert "−100,000" in run_row(show(panel, 400000))["text"]


def test_a_better_run_is_pending_and_a_worse_one_is_not_saved(panel):
    """taiko-web keeps the better score, so a lesser run never lands --
    saying "pending" about it would be a promise that is never kept."""
    assert "PENDING" in run_row(show(panel, 950000))["text"].upper()
    assert "NOT SAVED" in run_row(show(panel, 400000))["text"].upper()


def test_a_rank_is_left_off_when_the_board_runs_deeper_than_it_was_fetched(panel):
    """Five rows are fetched. Below those the rank is not ours to state."""
    rows = show(panel, 100000, players=50)
    assert run_row(rows)["rank"] == ""


def test_the_rank_is_given_when_the_whole_board_is_in_view(panel):
    rows = show(panel, 100000, players=3)
    assert run_row(rows)["rank"] == "4"


def test_a_first_ever_score_says_so(panel):
    rows = show(panel, 700000, board=[BOARD[0], BOARD[2]], players=2)
    assert "FIRST SCORE" in run_row(rows)["text"].upper()
