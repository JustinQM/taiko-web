# 04 — Dancers, on the beat

## What it is

Up to five dancers along the bottom of the background. Each has a start,
a loop and an end animation, and the loop runs at `(60000 / bpm) / 2`
per frame, so they move with the music rather than at a fixed rate. They
bounce in from off screen when play begins: up 350px over half a beat
eased out, then down 140 eased in, after a 500ms delay.

Those numbers are the skin's, from `bg_objects/dancer.lua`.

## What it changes

A `Dancer` drawn by the background from 03, reading the strips and
manifest from 02.

## How it will be shown to work

Frame advance matches the tempo: a 120bpm song advances a dancer frame
every 250ms, a 240bpm song every 125ms, measured rather than asserted
from the constant. The bounce completes before the first note. The frame
harness shows what five of them cost against none.
