# 06 — Remove the DOM and CSS background

Once the canvas background is drawing, the old one goes: `#songbg`, its
layers, the stage element, `songbg.css`, `setBackground`, `setDonBg` and
the `bg_song_*` and `bg_stage_*` assets they read.

Keeping both would mean carrying the placeholder art forever alongside
the thing meant to replace it.

## How it will be shown to work

No `songbg` element is created, `songbg.css` is gone from the asset list,
and the game still draws a complete background. Song skins that named a
custom stage fall back to the standard background rather than breaking.
