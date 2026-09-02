# 14 — The band above the lanes, and the flashing

The reported fault. The band above the note lanes flashes yellow and
red about twice a second.

The cause: `donbg`'s art has two frames and they are not an animation.
Frame 0 is the band; frame 1 is the same band lit up for when the gauge
reaches Clear. YataiDON draws frame 0 always, and fades frame 1 in over
it in 150ms when the player clears. The port treated the two frames as
a loop and cycled them on the beat.

While in there, the rest of what the band does:

* It scrolls. 328px every 3000ms, looping -- the band drifts sideways
  the whole song.
* Its overlay moves independently, and differently per set: a 1000ms
  bob for sets 0, 3 and 5, 1500ms for set 1, a quadratic bounce for
  sets 2 and 4, and set 5 has a second overlay moving at three times
  the speed of the first.
* Set 0 has a footer strip of its own, tiled 31 times across.
* Sets 3 and 5 are 11 and 6 tiles wide rather than 5.

## What it changes

`DonBG` in `gamebackground.js`, as six variants matching
`Scripts/background/bg_objects/donbg/{1..6}.lua`.

## How it will be shown to work

The clear fade is a test: hold the gauge over the clear line and the
overlay frame's alpha goes 0 to 1 once, over 150ms, and stays. Cross
back under and it drops to 0 and stays. At no point does the base frame
change.
