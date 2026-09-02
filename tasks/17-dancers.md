# 17 — Dancers: how many, where, and in what order

Four things differ from the skin, and the first is why the screen looks
busier than YataiDON's.

* **How many.** YataiDON starts with one dancer and earns the rest: the
  gauge is divided into five, and a dancer arrives at each fifth,
  the fifth only at Clear. Drop back below a mark and one leaves. The
  port put all five on screen from the first bar.
* **Where.** They fill five fixed slots, in the order centre, left,
  right, far-left, far-right -- so the first dancer stands in the middle
  and the group grows outward symmetrically. The port spaced whatever
  it had evenly, so every arrival shuffled the whole row sideways.
* **What order the frames go in.** Covered in task 12: the loop is a
  written-out sequence, not 0..n.
* **The entrance.** Each dancer has a `start` animation that plays once
  over a beat as it bounces in, then hands over to the loop. The port
  bounced the loop and never drew the start frames at all.

Two sets need more than the base dancer: set 0's fifth dancer carries a
bouncing object drawn from three extra frames, and sets 7, 8, 12, 13 and
16 puff into existence over seven frames.

Each dancer also stands at its own height -- 415, 365, 395, 430 within
one set -- which the manifest now carries.

## What it changes

`Dancer` and `DancerGroup` in `gamebackground.js`, from
`bg_objects/dancer.lua`, and the gauge milestone handling in the
orchestrator.

## How it will be shown to work

A test that drives the gauge from empty to full and counts dancers:
one, then two at a fifth, five at Clear, and back down again as the
gauge drops.
