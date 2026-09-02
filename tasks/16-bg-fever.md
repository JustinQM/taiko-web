# 16 — Fever, which is four different things

`bg_fever` is not one background with a variant; it is four bespoke
animations that share only a name.

* Set 0 expands twenty tiles out from the middle of the screen over
  1.3 seconds while a corner, a footer, a mountain and an overlay each
  bounce in 100ms behind the last, and a wave orbits a circle.
* Set 1 flies a ship in from the left and out again, with two birds and
  three footers, everything fading in over 416ms.
* Set 2 orbits sixteen fish around a rotating circle.
* Set 3 drops a tiled background 400px and lifts it 40 back, then
  scrolls it in both directions forever.

The port drew a mountain, a wave and an overlay for all four, which set
0 half-resembles and the other three do not have at all.

The rainbow overlay -- `fever`, drawn only when the gauge is full -- was
imported and never drawn.

## What it changes

`BGFever` as four variants and `Fever` as its two, from
`bg_objects/bg_fever.lua` and `bg_objects/fever.lua`, including the
transition: YataiDON keeps drawing the normal background under the fever
one until the fever animation says it has finished arriving.

## How it will be shown to work

Clear the gauge on a song mapped to each of the four and watch the
transition; a test that the normal background keeps drawing until
`transitioned` and stops after.
