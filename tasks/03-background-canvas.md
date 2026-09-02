# 03 — The background as a canvas layer

## What it replaces

`view.js` builds the background out of DOM: a `#songbg` element with two
layers and a stage image, animated by `songbg.css`. That is where the
placeholder art lives.

## What it changes

A `Background` object drawn on a canvas behind the game, holding the
structure YataiDON's Lua drives: `donbg`, `bg_normal`, `bg_fever`, and
later the rest. It draws in `view.refresh` before the lanes, and knows
about the song's BPM and the gauge state, which is what everything else
keys off.

The DOM background stays in place for this task and is removed in 06,
once there is something to remove it in favour of. Doing both at once
would mean no working background at any point in between.

## How it will be shown to work

The layers draw in the right order at the right scale, at several window
sizes. The frame harness from 01 shows what it costs. The public build,
with 1x1 placeholders, draws nothing and does not error.
