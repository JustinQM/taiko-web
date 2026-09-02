# 15 — The five standard backgrounds, whole

Sets 0 and 1 are a background and an overlay that flickers between 0.5
and 0.4 opacity every 67ms -- lantern light, not a strobe. The port drew
the overlay at a flat 0.75, which is both brighter and deader than the
skin.

The other three were never imported past their base layer:

* Set 2 is a stadium: a centre piece, two lamps (the second mirrored),
  four coloured lights that flicker together, and three side pieces.
* Set 3 is a cherry-blossom night: a character, a turtle that crosses
  the screen over 6.6 seconds changing through six frames, and five
  petals that respawn as they fall.
* Set 4 is a row of ten paper lanterns, each drawn on a different frame,
  with a light overlay that flickers between 0.75 and 0.4.

## What it changes

`BGNormal` in `gamebackground.js`, as the five variants of
`bg_objects/bg_normal.lua`, drawing every layer at the position its
`texture.json` gives.

## How it will be shown to work

A screenshot per set, and a check that every layer named in the Lua is
present in the manifest.
