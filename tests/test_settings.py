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


SPARTAN_ROWS = ["Spartan Mode: GOOD", "Spartan Mode: OK", "Spartan Mode: BAD"]


def test_spartan_rows_render_their_options(game):
    """The plugin's own settings UI was broken exactly here.

    getValue labels a select from strings.settings[name][value]. For a
    plugin setting `name` is the array index it arrived at, so the lookup
    was undefined and the row threw. As built-in settings the labels
    resolve, so this walks every option of every row.
    """
    game.open_settings()
    expected = {"Continue", "Results", "Retry", "Back to Select Song"}
    for name in SPARTAN_ROWS:
        seen = {game.row(name)["value"].strip()}
        for _ in range(3):
            game.click(name)
            seen.add(game.row(name)["value"].strip())
        assert seen == expected, f"{name} cycled through {seen}"
    assert game.errors == []


def test_spartan_defaults_are_inert(game):
    """The plugin shipped with start: false, so nothing should happen."""
    game.open_settings()
    for key in ["spartanGood", "spartanOk", "spartanBad"]:
        assert game.setting(key) == "continue", f"{key} defaults to something else"


def test_spartan_bad_ends_the_song_and_counts_the_rest(game):
    """Drive checkSpartanMode directly; playing a song needs real audio.

    Three unplayed notes remain, so ending here has to add three bads and
    trip the fade-out, or the results screen disagrees with the note count.
    """
    game.open_settings()
    result = game.page.evaluate("""() => {
        settings.setItem('spartanBad', 'results')
        const fake = {
            multiplayer: 0,
            controller: {autoPlayEnabled: false},
            globalScore: {bad: 0},
            fadeOutStarted: null,
            songData: {circles: [
                {type: 'don', isPlayed: true},
                {type: 'don', isPlayed: false},
                {type: 'ka',  isPlayed: false},
                {type: 'daiKa', isPlayed: false},
                {type: 'balloon', isPlayed: false},
                {type: 'don', isPlayed: false, branch: {active: false}}
            ]}
        }
        Game.prototype.checkSpartanMode.call(fake, -1)
        return {bad: fake.globalScore.bad, fadeOut: fake.fadeOutStarted}
    }""")
    assert result["bad"] == 3, f"counted {result['bad']} remaining notes, expected 3"
    assert result["fadeOut"] == float("-inf"), "song was not ended"


def test_spartan_is_inert_in_multiplayer_and_autoplay(game):
    game.open_settings()
    untouched = game.page.evaluate("""() => {
        settings.setItem('spartanBad', 'results')
        const make = over => Object.assign({
            multiplayer: 0,
            controller: {autoPlayEnabled: false},
            globalScore: {bad: 0},
            fadeOutStarted: null,
            songData: {circles: [{type: 'don', isPlayed: false}]}
        }, over)
        const results = []
        for(const fake of [make({multiplayer: 1}),
                           make({controller: {autoPlayEnabled: true}})]){
            Game.prototype.checkSpartanMode.call(fake, -1)
            results.push(fake.globalScore.bad === 0 && fake.fadeOutStarted === null)
        }
        return results
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
    # Only the face buttons swap. The shoulders are not labelled A or B
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
