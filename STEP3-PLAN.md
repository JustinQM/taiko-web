# Step 3 — backgrounds, the dojo, and native scores

Status: **in progress.** Written after investigating each, before starting.

Four pieces of work, in the order I intend to do them rather than the
order they were asked for: the bug first because it is small and wrong
every time you finish a song, then the two contained features, then the
big one.

---

## 1. Losing your place after a song

**The bug.** Finishing a song puts you back at the root of the wheel
rather than on the song you just played, inside the folder it was in.

**Why.** The scoresheet builds a fresh `SongSelect`, which restores
`localStorage["selectedSong"]` -- and that is an index into whatever
listing was open. When folders arrived I made it only persist at the
root, precisely because an index means nothing against a different
listing. So inside a folder nothing is remembered at all.

**The fix.** Persist the folder path alongside the index, and have
`SongSelect` walk back to it on construction. `navigator.pathIds()` and
`goToPath()` already exist for netplay and do exactly this.

*Verify:* finish a song inside a genre, land back on it; the same for a
nested folder and for Favourites; a stale path from a database that no
longer has that folder falls back to the root rather than breaking.

## 2. Scores in the game, not only in the panel

**Now.** `public/src/custom.js` injects a leaderboard into the page as a
DOM overlay, scoped under `#hs`, deliberately behaving like a guest on
someone else's page. It is a separate design from the game around it.

**Wanted.** The scores should read as part of the game -- drawn where the
game draws, in the game's own idiom -- while the website stays as it is
and can still be opened.

**Approach.** The leaderboard's data already comes from
`/highscores/api/song/<id>`, which is a clean JSON boundary. Keep the
service and the endpoint untouched; replace the panel's presentation with
something drawn into the difficulty screen, where a song is already
selected and there is room beside the courses. Keep a way out to the full
site for anything the in-game view does not show.

*Verify:* the scores shown match the API for that song; the difficulty
screen still works with the service down; the website is unchanged.

## 3. The dojo

**What it is.** A ranked series of song sets with pass conditions --
YataiDON has `11 Dan Dojo` as a root folder, `dan_select` as its own
scene, and `DanBackground` as a collab background. taiko-web has no
concept of it at any level: no schema, no UI, no scoring.

**Feasibility, honestly.** The parts are: a dan definition (a set of
songs with per-course requirements), a database collection to hold them,
an import path, a select screen, a chained player that runs three songs
without returning to song select, running totals against pass conditions,
and a result screen. That is a feature the size of the folder tree, not
an afternoon.

**Multiplayer.** The netplay protocol carries a selection and a note
stream. A dan is a sequence with shared state across songs; keeping two
peers in step through three chained songs and a shared pass condition is
a protocol change on top of the feature. I am **not** attempting that --
single player only, and I will say what it would take.

**Scope here.** The data model, the import path and enough of the flow to
play a dan through and be judged on it. Not the presentation YataiDON
gives it.

## 4. Backgrounds and dancers

**How YataiDON does it.** Entirely in the skin, as Lua: 245 lines
orchestrating eight objects totalling 1430 more, plus ten collab
backgrounds for specific licences. The standard background composes
`donbg`, `bg_normal` (5 variants), `bg_fever` (4), `fever` (4), `dancer`
(21 sets), `footer` (3), `renda` and `chibi`, all driven off the song's
BPM -- a dancer's loop is `(60000 / bpm) / 2` per frame, so they move in
time with the music, and they bounce in from off screen when play starts.

**The assets.** 55MB, of which the dancers are 45MB across 1993 files:
21 sets, each with start, loop and end animations for up to five dancers.
taiko-web loads every asset it lists at startup, so 1993 files is not
something to hand it -- they have to be composited into strips first.

**What ours does now.** A DOM and CSS background: `songbg` with two
layers and a stage image, animated by `songbg.css`. That is what the
placeholder art is sitting in.

**Scope.** The standard background only, no collabs: the layered
background, the fever variant, the footer, and one dancer set of the
five-dancer arrangement, composited into strips and drawn on a canvas
behind the game. Chibi and renda if they fall out cheaply.

*Verify:* dancers move in time with the song's BPM at several tempos;
the background changes on a full gauge; nothing draws in the public
build; frame rate holds on the local stack.

---

## Not in scope

The ten collab backgrounds, dan in multiplayer, the 3D character, and
anything that would put asset material in the public repo.
