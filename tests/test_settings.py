"""Tests for the settings screen.

These cover the shapes of bug this project has actually hit, rather than
aiming at coverage:

- the screen throwing during init, which takes the whole screen down and
  showed up as a blank page
- a setting that does not persist across a reload
- a row rendering wrong -- a missing label, an empty value, or a literal
  "undefined" from a strings lookup that does not exist
"""

import pytest


def test_settings_screen_opens_without_errors(game):
    game.open_settings()
    assert game.errors == [], f"settings screen raised: {game.errors}"
    assert len(game.rows()) > 0


def test_every_row_has_a_label_and_a_value(game):
    """Catches missing strings entries and broken value lookups.

    A row whose strings entry is absent renders its name or value as
    "undefined" rather than throwing, so the screen still opens and the
    breakage is only visible on screen. That is how the spartan mode
    plugin's settings UI was broken without anyone noticing.
    """
    game.open_settings()
    for row in game.rows():
        name, value = row["name"].strip(), row["value"].strip()
        assert name, f"setting row with no label: {row}"
        assert "undefined" not in name, f"unresolved label: {name!r}"
        assert "undefined" not in value, f"unresolved value for {name!r}: {value!r}"
        assert "[object Object]" not in value, f"unformatted value for {name!r}: {value!r}"


def test_expected_settings_are_present(game):
    game.open_settings()
    names = [row["name"].strip() for row in game.rows()]
    for expected in ["Language", "TJA Title", "Game Resolution", "Easier Big Notes"]:
        assert expected in names, f"{expected!r} missing from {names}"


def test_toggle_persists_across_reload(game):
    """A setting has to survive both a redraw and a page load."""
    game.open_settings()
    before = game.setting("easierBigNotes")

    game.click("Easier Big Notes")
    after = game.setting("easierBigNotes")
    assert after != before, "clicking the row did not change the value"
    assert game.stored("easierBigNotes") == after, "value was not written to localStorage"

    game.load().open_settings()
    assert game.setting("easierBigNotes") == after, "value did not survive a reload"
    assert game.errors == []


def test_select_cycles_through_its_options(game):
    """Select rows step to the next option and label it from strings."""
    game.open_settings()
    seen = [game.row("Game Resolution")["value"].strip()]
    for _ in range(3):
        game.click("Game Resolution")
        seen.append(game.row("Game Resolution")["value"].strip())

    assert all(seen), f"a resolution step rendered an empty value: {seen}"
    assert len(set(seen)) > 1, f"value never changed: {seen}"
    assert game.errors == []


def test_song_select_speed_is_a_number_setting(game):
    """The scroll speed absorbed from the change-song-select-speed plugin.

    A number setting is the case that used to throw during init, so this
    checks the row renders, formats and persists rather than just that the
    value exists.
    """
    game.open_settings()
    row = game.row("Song Select Speed")
    assert row["value"].strip().endswith("x"), f"unformatted: {row['value']!r}"
    assert game.setting("songSelectSpeed") == 2, "default should be 2"
    assert game.errors == []


def test_song_select_speed_persists_and_is_applied(game):
    game.open_settings()
    game.page.evaluate("() => settings.setItem('songSelectSpeed', 4)")

    game.load()
    assert game.setting("songSelectSpeed") == 4, "value did not survive a reload"

    # The wheel reads the setting when SongSelect is constructed, as
    # 400 / speed, so a higher setting means a shorter step.
    applied = game.page.evaluate(
        "() => { const s = new SongSelect(false, true); "
        "const v = s.songSelecting.speed; s.clean(); return v }"
    )
    assert applied == 100, f"expected 400/4, got {applied}"
    assert game.errors == []
