# 11 — Performance: measure, then fix

Not a footnote. Dropped frames in a rhythm game cost notes.

## Measure first

Using the harness from 01, on the private stack, playing real songs:
where is the time going, per scene. No fixes before there are numbers.

## Known and suspected

- **The fireworks stutter.** `drawHitFireworks` loops up to sixteen
  bursts per big note, each a `drawImage` of `tja_hit_fireworks_keyed`
  under `globalCompositeOperation = "lighter"`. In the public build that
  asset is a 1x1 placeholder scaled to full size, which is a different
  cost from the real sheet. Both need measuring: the loop may be the
  cause, the compositing mode may be, or the scaling of a 1x1 may be.
- **Startup loading.** Everything listed loads before the title screen,
  and the backgrounds make that much worse. What can be deferred to
  first use, what should be one strip instead of many files, what is
  being decoded more than once.
- **canvascache.js** exists to cache drawn output. Check it is used
  where it matters and that its keys are not missing.
- **Per-frame allocation and layout.** Anything allocating objects or
  reading layout inside the draw loop.

## How it will be shown to work

The numbers from 01, before and after, for each scene. A named
improvement for each change, and an honest note where something was tried
and did not help.
