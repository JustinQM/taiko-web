# 13 — YataiDON's animation primitives, ported rather than approximated

Every moving thing in YataiDON's background is one of three animations
declared in `background/animation.json` and driven by a shared base
class: a move, a fade, or a texture change. They have delays, easing,
looping, and a `reverse_delay` that turns a one-way move into a
ping-pong.

The first pass reimplemented a few of them inline with hand-written
curves, which is why the numbers in the code had to be explained in
comments -- they had been copied out of their context.

## What it changes

`public/src/js/bganim.js`: `BgAnim.move`, `BgAnim.fade` and
`BgAnim.textureChange`, ported from `src/libs/animation.cpp` with the
same easing, the same delay handling and the same reverse-then-finish
behaviour, plus the loader for `animation.json`'s own declarations
(including the `delay: {reference_id, property}` references, which is
how the skin chains one animation behind another).

## How it will be shown to work

Tests drive the animations directly at chosen timestamps and check the
attribute against the C++ arithmetic, including the awkward cases: a
delay before the start, a reverse at the end, a loop restarting.
