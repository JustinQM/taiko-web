"""The volume setting.

One multiplier over every gain, so turning the game down does not disturb
the balance between music, effects and previews that the rest of the code
sets up.
"""

import pytest


def test_volume_is_a_setting(game):
    game.open_settings()
    row = game.row("Volume")
    assert row["value"].strip().endswith("%"), f"unformatted: {row['value']!r}"
    assert game.errors == []


def test_it_reaches_the_audio_graph(game):
    applied = game.page.evaluate("""() => {
        settings.setItem("volume", 50)
        return snd.buffer.masterVolume
    }""")
    assert applied == pytest.approx(0.5)


def test_it_scales_every_gain(game):
    """Not just the one that happens to be playing."""
    louder, quieter = game.page.evaluate("""() => {
        const read = () => [snd.musicGain, snd.sfxGain, snd.previewGain]
            .map(g => g.gainNode.gain.value)
        settings.setItem("volume", 100)
        const loud = read()
        settings.setItem("volume", 25)
        return [loud, read()]
    }""")
    assert all(q < l for q, l in zip(quieter, louder)), \
        f"a gain did not follow the setting: {louder} -> {quieter}"


def test_the_balance_between_gains_is_kept(game):
    """Turning it down must not change their relative levels."""
    ratios = game.page.evaluate("""() => {
        const ratio = () => {
            snd.musicGain.setVolume(0.8)
            snd.sfxGain.setVolume(0.4)
            return snd.musicGain.gainNode.gain.value / snd.sfxGain.gainNode.gain.value
        }
        settings.setItem("volume", 100)
        const loud = ratio()
        settings.setItem("volume", 30)
        return [loud, ratio()]
    }""")
    assert ratios[0] == pytest.approx(ratios[1]), \
        f"the balance shifted with the volume: {ratios}"


def test_zero_is_silent(game):
    silent = game.page.evaluate("""() => {
        settings.setItem("volume", 0)
        snd.sfxGain.setVolume(1)
        return snd.sfxGain.gainNode.gain.value
    }""")
    assert silent == 0


def test_it_survives_a_reload(game):
    game.page.evaluate("() => settings.setItem('volume', 40)")
    game.load()
    assert game.setting("volume") == 40
    assert game.page.evaluate("() => snd.buffer.masterVolume") == pytest.approx(0.4)


def test_the_default_button_reapplies_it(game):
    """Default writes every item back without going through the screen's
    own handler, so applying from the screen would have missed it."""
    game.open_settings()
    game.page.evaluate("() => settings.setItem('volume', 10)")
    game.page.evaluate("() => { const v = settings.items.volume.default; settings.setItem('volume', null) }")
    default = game.setting("volume")
    assert game.page.evaluate("() => snd.buffer.masterVolume") == pytest.approx(default / 100)
