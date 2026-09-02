# 02 — Composite the background art into strips

## The problem

55MB across 2500 files, of which the dancers are 45MB in 1993: 21 sets,
each with start, loop and end animations for up to five dancers.
taiko-web loads every asset it lists at startup. Handing it two thousand
files is not an option.

## What it changes

`tools/import-yatai-backgrounds.sh` in the private repo, beside the
existing import pipeline. For each animation directory it writes one
horizontal strip, and a JSON manifest of frame counts and sizes so the
game does not have to guess.

- `dancer/dancer_N/M_{start,loop,end}` → one strip each
- `bg_normal/bg_N`, `bg_fever/bg_fever_N`, `fever/fever_N`, `donbg`,
  `footer`, `renda`, `chibi` → the same treatment

Only the sets actually shipped are composited. 21 dancer sets is more
variety than the deployment needs and each is 2MB; a subset keeps the
image sane, and the number is one constant.

## How it will be shown to work

Every strip's frame count matches the directory it came from, and one
frame sliced back out of a strip is byte-identical to its source file.
The manifest agrees with the strips. Nothing lands in the public repo —
`check-no-assets.sh` still passes.
