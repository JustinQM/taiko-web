# 24 — The background and the window

Reported as still broken, and it is fixed -- behind the cache in task
19. Worth checking properly rather than asserting it, and worth writing
down what YataiDON actually does, because it is not what we do and the
difference is the reason.

**YataiDON draws its whole game into a fixed 1280x720 screen** and then
scales that one image to the window with `min(w/1280, h/720)`, centred,
filling whatever is left over with a solid colour (`draw_outer_border`).
Nothing sticks out into the border because nothing is outside the
virtual screen. It never stretches the background, because it never has
to.

taiko-web is not built that way: the lanes, the header and Don-chan are
drawn at the window's width while the background art is a 1280-wide
design. Letterboxing the whole game to match YataiDON would shrink
everything on a wide monitor. So the background reaches the edges
instead -- which is what the DOM background it replaced did.

## What it changes

Nothing, if it checks out. Confirm at several aspect ratios that there
is no bar and no flicker.
