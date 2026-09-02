# 07 — Crowns from the skin

The crown is drawn from a hand-authored SVG path in `vectors.json`,
patched in by the private overlay. It reads as approximate next to
everything around it.

## What it changes

The skin has crown art. Import it as images and draw those instead of
the path, keeping the path as the public build's fallback so nothing
depends on private art.

## How it will be shown to work

Crowns render from the image where one exists and from the path where it
does not, at every size they are drawn — song select, the difficulty
screen, the results screen.
