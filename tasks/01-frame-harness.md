# 01 — A repeatable frame-time harness

Frame timing is not something the existing tests can tell you about, and
"it feels smoother" is not a result. This is the instrument the
performance pass reports against, and it has to exist before the
backgrounds land so there is a before to compare with.

## What it changes

`tests/perf/` — a harness, not a test. Drives a real browser against the
private stack, plays a song with autoplay, and records per-frame times
from inside the page.

Measured, per scene (song select, gameplay, the ending):

- median, 95th and 99th percentile frame time
- the count of frames over 16.7ms and over 33ms, which are the ones that
  cost notes
- the worst single frame and when it happened

It writes a JSON file so runs can be compared, and prints a table.

## How it will be shown to work

Two runs of the same build land within noise of each other — if the
harness is not repeatable it cannot show a regression. Then a
deliberately slowed frame (a busy loop injected into the draw) shows up
in the numbers.

It runs against `:34900`, the private stack, because that is the one with
real assets and playable songs. The public stack has neither and would
measure something that does not exist.
