"""Tests for skipping the results screen in multiplayer.

Absorbed from the skip-results-in-multiplayer plugin. A real end-to-end
check would need two browsers in a netplay session playing a song, and
the dev stack has no song audio, so these drive the Scoresheet methods
directly against a stubbed p2 connection. That still exercises the real
branching, which is where this change actually lives.
"""

import pytest

# Replaces the global p2 for one call and reports what was sent.
DRIVER = """
(args) => {
    const {method, fromP2, session, player} = args
    const real = p2
    const sent = []
    try {
        p2 = {
            session: session,
            player: player,
            send: (type, value) => sent.push({type: type, value: value}),
            getMessage: () => null,
        }
        const sheet = {
            state: {screen: "fadeIn", screenMS: 0},
            session: session,
            getMS: () => 0,
            controller: {playSound: () => {}},
            playSound: () => {},
        }
        Scoresheet.prototype[method].call(sheet, fromP2)
        return {sent: sent, screen: sheet.state.screen}
    } finally {
        p2 = real
    }
}
"""


@pytest.fixture
def drive(game):
    def run(method, fromP2=False, session=True, player=1):
        return game.page.evaluate(
            DRIVER,
            {"method": method, "fromP2": fromP2, "session": session, "player": player},
        )
    return run


def test_scores_can_be_skipped_in_a_session(drive):
    """The whole point: in a session this used to do nothing at all."""
    result = drive("toScoresShown")
    assert result["screen"] == "scoresShown", "the screen did not advance"


def test_skipping_tells_the_peer(drive):
    result = drive("toScoresShown")
    notes = [m for m in result["sent"] if m["type"] == "note"]
    assert len(notes) == 1, f"expected one note, sent {result['sent']}"
    assert notes[0]["value"]["skipResults"] is True
    # Sent as a note so a peer running stock taiko-web reads it as one.
    assert notes[0]["value"]["score"] == 450


def test_a_skip_from_the_peer_is_not_echoed_back(drive):
    """Otherwise the two clients bounce skips off each other."""
    result = drive("toScoresShown", fromP2=True)
    assert result["screen"] == "scoresShown"
    assert result["sent"] == [], f"echoed back: {result['sent']}"


def test_leaving_for_song_select_takes_the_peer(drive):
    result = drive("toSongsel")
    types = [m["type"] for m in result["sent"]]
    assert "songsel" in types, f"peer not told to leave: {result['sent']}"


def test_peer_initiated_songsel_is_not_echoed_back(drive):
    result = drive("toSongsel", fromP2=True)
    assert result["screen"] == "fadeOut"
    assert result["sent"] == [], f"echoed back: {result['sent']}"


def test_single_player_is_unchanged(drive):
    """No session means no messages and the original sound behaviour."""
    shown = drive("toScoresShown", session=False)
    assert shown["screen"] == "scoresShown"
    assert shown["sent"] == []

    songsel = drive("toSongsel", session=False)
    assert songsel["screen"] == "fadeOut"
    assert songsel["sent"] == []
