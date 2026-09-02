# 12 — Import the whole background, not a guess at its shape

The first import assumed every background set had the same pieces:
a background, an overlay, a mountain, a wave, a footer. That is true
of exactly one of the nine sets.

What actually shipped:

* `bg_fever` 1, 2 and 3 lost their background entirely — 1 and 2 keep
  theirs in a file rather than a folder, and the importer only looked
  for folders. Reaching Clear on a song that drew one of those made the
  lower half of the screen go empty.
* `bg_normal` 2, 3 and 4 lost every layer but two. Set 2 is a stadium
  built from eleven pieces; what got imported was the 8px gradient it
  tiles behind them.
* `donbg` shipped three of six sets and dropped the second overlay that
  set 5 is mostly made of.
* Nothing carried the positions. YataiDON places every piece from a
  `texture.json` next to the art; the game was left guessing.
* Nothing carried `frame_order`. A dancer's loop is not frames 0..n --
  it is a written-out sequence that goes forward, back and around
  (`0,1,2,1,0,1,2,3,9,7,4,...`). Played in file order the dance is not
  the dance.

## What it changes

`tools/import-yatai-backgrounds.py` replaces the shell script. It walks
the skin folder rather than being told what to expect: every `x.png`
becomes a one-frame asset, every `x/` becomes a strip, `texture.json`
supplies the positions, and `frame_order` decides what order the frames
go into the strip so the game can keep playing them 0..n-1.

## How it will be shown to work

The manifest lists every layer YataiDON's scripts ask for, checked
against the scripts rather than by eye. Frames come back out of a strip
identical to the source file `frame_order` names.
