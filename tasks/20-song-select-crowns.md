# 20 — Crowns in song select, at the skin's size

Both of them are small, and both for the same reason as the results
crown: they are drawn into the 94x78 box the vector fallback occupies
and then scaled down from it.

* The crown above a closed song box is drawn at 0.3 of the box, so
  28x23. YataiDON's is 40x40.
* The per-difficulty crowns inside the opened box are drawn at 0.25, so
  23x19. YataiDON's are 56x56 -- and they are not the same art: the
  yellow box has its own crowns with five frames, one per difficulty,
  outlined to match.

## What it changes

The 56px crowns get imported, which they never were. Both call sites ask
for the skin's size rather than a fraction of the fallback's box.

## How it will be shown to work

Side by side with the skin at the same zoom.
