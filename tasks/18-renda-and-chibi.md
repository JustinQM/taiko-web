# 18 — The two things that react to playing

Neither was ported.

**Renda** is the character that runs across the background when you hit
a drumroll or a balloon. Three variants: one falls while it crosses, one
spins, one is plain.

**Chibi** is the small character that crosses the background on every
Good and OK -- and a different, sadder one on a Bad, which fades in over
half a beat. Fourteen sets, of which seven have their own behaviour.

Both need the game to tell the background what happened, which nothing
currently does.

## What it changes

`Renda` and `Chibi` in `gamebackground.js`, and the calls from the
judgement path that feed them -- the same four hooks YataiDON's player
calls: good, ok, bad, drumroll/balloon.

## How it will be shown to work

Hit a drumroll and a character crosses; miss a note and the sad one
does. A test that a Bad adds one and that they are dropped once they
leave the screen rather than accumulating for the length of the song.
