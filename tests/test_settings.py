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
    assert game.setting("songSelectSpeed") == 1, "1x should be the default"
    assert game.errors == []


def test_song_select_speed_persists_and_is_applied(game):
    game.open_settings()
    game.page.evaluate("() => settings.setItem('songSelectSpeed', 4)")

    game.load()
    assert game.setting("songSelectSpeed") == 4, "value did not survive a reload"

    # The wheel reads the setting when SongSelect is constructed, so a
    # higher setting means a shorter step.
    def step_duration():
        return game.page.evaluate(
            "() => { const s = new SongSelect(false, true); "
            "const v = s.songSelecting.speed; s.clean(); return v }"
        )

    at_four = step_duration()
    game.page.evaluate("() => settings.setItem('songSelectSpeed', 1)")
    at_one = step_duration()

    assert at_four == pytest.approx(at_one / 4), \
        f"the setting does not scale the step: 1x gave {at_one}, 4x gave {at_four}"
    # 1x is YataiDON's 166ms per step.
    assert at_one == pytest.approx(166, abs=1), f"1x step is {at_one}ms"
    assert game.errors == []


# One row now, and its options name the run being asked for rather than
# what to do about each judgement. There is no GOOD entry and never was:
# stopping the song because a note was played correctly is not a mode
# anyone wants.
SPARTAN = "Spartan Mode"


def test_spartan_renders_its_options(game):
    """The plugin's own settings UI was broken exactly here.

    getValue labels a select from strings.settings[name][value], and a
    row whose options have no strings shows blank or throws.
    """
    game.open_settings()
    expected = {"Off", "Full Combo", "Donderful Combo"}
    seen = {game.row(SPARTAN)["value"].strip()}
    for _ in range(3):
        game.click(SPARTAN)
        seen.add(game.row(SPARTAN)["value"].strip())
    assert seen == expected, f"cycled through {seen}"
    assert game.errors == []


def test_spartan_is_off_by_default(game):
    """The plugin shipped with start: false, so nothing should happen."""
    game.open_settings()
    assert game.setting("spartanMode") == "off"
    assert game.row(SPARTAN)["value"].strip() == "Off"


def test_spartan_has_no_rows_hidden_behind_it(game):
    """It was a group opening onto two more rows. One row, no submenu."""
    game.open_settings()
    names = game.page.eval_on_selector_all(
        ".settings-outer > .view > .view-content > .setting-box",
        """els => els.map(e => e.querySelector(".setting-name").textContent.trim())""")
    assert SPARTAN in names
    assert "On an OK" not in names and "On a BAD" not in names


def spartan_fires(game, mode, score):
    """Whether a judgement ends the run. Driven directly: playing a song
    needs real audio, and the whole point is what happens mid-song."""
    return game.page.evaluate("""([mode, score]) => {
        settings.setItem('spartanMode', mode)
        let restarted = false
        const fake = {
            multiplayer: 0,
            controller: {autoPlayEnabled: false, restartSong: () => { restarted = true }}
        }
        Game.prototype.checkSpartanMode.call(fake, score)
        return new Promise(r => setTimeout(() => r(restarted), 30))
    }""", [mode, score])


# 450 is a GOOD, 230 an OK, 0 a BAD, -1 a note gone by unplayed.
def test_off_never_fires(game):
    game.open_settings()
    for score in (450, 230, 0, -1):
        assert spartan_fires(game, "off", score) is False, score


def test_a_full_combo_run_ends_on_a_bad_but_not_an_ok(game):
    game.open_settings()
    assert spartan_fires(game, "fc", 0) is True, "a bad did not end it"
    assert spartan_fires(game, "fc", -1) is True, "a missed note did not end it"
    assert spartan_fires(game, "fc", 230) is False, "an ok ended a full combo run"
    assert spartan_fires(game, "fc", 450) is False, "a good ended it"


def test_a_donderful_run_ends_on_an_ok_too(game):
    game.open_settings()
    assert spartan_fires(game, "dc", 230) is True, "an ok did not end it"
    assert spartan_fires(game, "dc", 0) is True
    assert spartan_fires(game, "dc", -1) is True
    assert spartan_fires(game, "dc", 450) is False, "a good ended it"


def test_spartan_is_inert_in_multiplayer_and_autoplay(game):
    game.open_settings()
    untouched = game.page.evaluate("""() => {
        settings.setItem('spartanMode', 'dc')
        const make = over => {
            const fake = Object.assign({
                multiplayer: 0,
                controller: {autoPlayEnabled: false, restartSong: () => { fake.hit = true }}
            }, over)
            fake.hit = false
            return fake
        }
        const a = make({multiplayer: 1})
        const b = make({controller: {autoPlayEnabled: true, restartSong: () => {}}})
        Game.prototype.checkSpartanMode.call(a, -1)
        Game.prototype.checkSpartanMode.call(b, -1)
        return new Promise(r => setTimeout(() => r([!a.hit, !b.hit]), 30))
    }""")
    assert untouched == [True, True], "spartan mode fired in multiplayer or autoplay"




def test_the_nintendo_pad_layout_is_type_b_the_other_way_round(game):
    """A pad in Nintendo mode reports its buttons by label rather than by
    position, so the button marked A arrives where an Xbox pad puts the
    bottom one. Every layout that names those buttons came out mirrored
    and the only way to play was to switch the pad to Xbox mode."""
    layouts = game.page.evaluate("""() => ({
        b: GameInput.gamepadLayout("b"),
        d: GameInput.gamepadLayout("d")
    })""")
    b, d = layouts["b"], layouts["d"]
    faces = lambda buttons: [x for x in buttons if x in ("a", "b", "x", "y")]
    assert b["game"]["don_l"] == d["game"]["don_l"], "the d-pad is unchanged"
    assert b["game"]["ka_l"] == d["game"]["ka_l"]
    # Only the face buttons swap. The shoulders are not labeled A or B
    # and mean the same thing whichever mode the pad is in.
    assert faces(b["game"]["don_r"]) == faces(d["game"]["ka_r"])
    assert faces(b["game"]["ka_r"]) == faces(d["game"]["don_r"])
    assert "rs" in d["game"]["don_r"] and "rb" in d["game"]["ka_r"]


def test_the_nintendo_layout_swaps_confirm_and_back_too(game):
    """The button the player reads as A has to confirm, whichever index
    the pad reports it under."""
    menus = game.page.evaluate("""() => ({
        b: GameInput.gamepadLayout("b").menu,
        d: GameInput.gamepadLayout("d").menu
    })""")
    assert menus["b"]["cancel"] == ["a"] and menus["b"]["confirm"][0] == "b"
    assert menus["d"]["cancel"] == ["b"] and menus["d"]["confirm"][0] == "a"
    assert menus["b"]["previous"] == menus["d"]["previous"], "movement is unchanged"


def test_the_nintendo_layout_is_offered(game):
    game.open_settings()
    assert game.setting("gamepadLayout") == "a"
    offered = game.page.evaluate(
        "() => settings.items.gamepadLayout.options")
    assert offered == ["a", "b", "c", "d"]
