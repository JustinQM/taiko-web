# Step 2 — song select as a folder tree

Status: **draft, awaiting review.** Nothing has been executed.

Goal: replace the single flat wheel of 3367 songs with a navigable folder
tree — genres at the top, favourites as their own folder, YataiDON's
navigation feel — plus three pieces of polish and one real bug.

---

## What I found

### The renderer is not the problem

`redraw()` is 1470 lines (songselect.js:1883-3350) and I expected it to be
the obstacle. It is not. It draws from exactly two things:

- `this.songs`, a flat array
- `this.selectedSong`, an index into it, wrapped with `this.mod()`

Everything else — the category bands, the crowns, the closed-song boxes,
the preview audio, the option menu — hangs off those. `this.songs` is
built once in `init()` (songselect.js:118-214): every song from
`assets.songs`, sorted by category, then the menu entries (random, search,
tutorial, about, settings, custom songs) appended.

So the restructure is: **change what populates `this.songs`, not how it is
drawn.** A folder listing is a flat array too. Descending into a folder
replaces the array and resets the index; ascending restores them. The
renderer never needs to know there is a tree.

That is what makes this tractable, and it is why stage 2 below is a pure
no-op refactor — introduce the navigator, have it produce exactly today's
list, change nothing on screen.

### The netplay protocol is the real constraint

`moveToSong` sends `p2.send("songsel", {song: <index>})`
(songselect.js:1547), `categoryJump` sends `catjump` with an index and a
direction (1593), and `onsongsel` (4161) applies them by index into
`this.songs`.

**Those indices are only meaningful if both peers have the same list.**
The moment one player descends into a folder, index 12 means different
things on the two screens, and the peers desync into selecting different
songs. Nothing in the protocol carries the folder.

This is the one part that cannot be staged around, so it gets its own
stage and its own decision below. It is also why I would not ship folders
and netplay in the same stage.

### The tree can come from data we already have

Two sources, and they disagree about what the top level is:

- `song.category` / `category_id` — the 8 genres in the `categories`
  collection. This is what the wheel's colour bands already use.
- `manifest.json`'s `rel` field — the path in the OpenTaiko source tree,
  which `tools/scan.py` already records and `tools/import.py` already
  drops on the floor. 3317 of 3367 songs sit two levels deep
  (`ese/01 Pop/<song>`), 50 sit three (`OpenTaiko/L1 Collaborations/C01
  Project Outfox Serenity/<song>`).

You asked for genre at the top, so: **genre folders from `category_id`,
sub-folders from what is left of `rel` inside them.** For the `ese/*`
songs `rel` adds nothing (its second component *is* the genre), so those
genres are flat inside — which is correct, they have no substructure. The
OpenTaiko packs get their chapters and collaborations as real sub-folders.

This needs a new `folder` field on song documents, written by `import.py`.
Songs already in mongo do not have it, so the client treats it as optional
and falls back to genre-only until you re-import. Nothing breaks in the
meantime.

The whole song list is already client-side — `/api/songs` returns all 3367
at load — so the tree is computed in the browser. No new API for
navigation. Favourites are the only thing that needs the server.

### Favourites have no precedent here

You are right that taiko-web has no concept of them. The nearest pattern
is `scoreStorage`: server-backed when logged in (`/api/scores/save`,
`/api/scores/get`, keyed on `session['username']`), localStorage when not.
Favourites should follow it exactly rather than invent a second shape.

### The three polish items

- **Ending animation.** `se_gameclear.ogg`, `se_gamefail.ogg`,
  `se_gamefullcombo.ogg` and `se_gamedonderfulcombo.ogg` are listed in
  `assets.js:220-223` and referenced *nowhere else in the codebase*. There
  is no animation code at all. Confirmed by grep across `public/src/js`.
- **Rainbow soul flame.** `draw.soul()` is called at view.js:552 and 650.
  There is no flame.
- **The P2 rainbow gauge bug is real and I found it.**
  `drawGaugeRainbow` (canvasdraw.js:1421) computes
  `var dy = config.multiplayer ? -8 : -8` — a ternary whose arms are
  identical. Someone meant to offset it for P2 and never filled it in.
  The gauge body genuinely is drawn differently for P2 (`firstTop`/
  `secondTop` flip from 30/8 to 0/0 at canvasdraw.js:1470, and the rounded
  corners mirror), so the rainbow overlay lands in the wrong place. The
  fix is the offset plus, most likely, a vertical flip to match; I will
  confirm the exact geometry against a running P2 session.

### Assets

All of them exist. `Skins/` are gitea submodules on `ese.tjadataba.se`,
which is reachable — `git submodule update --init --depth 1
Skins/PyTaikoGreen` worked. `Graphics/game/ending_anim/` has clear,
full_combo, fail, their highlights, `bachio_l/r_{in,fall,out}`, `fan_l/r`,
`sparkle`, a 5-frame `confetti/` directory and a `texture.json`.
`Graphics/game/gauge/tamashii_fire/` has the 8 frames.

Two are frame directories rather than sheets, and taiko-web's loader wants
one image per asset, so they get composited into strips. `imagemagick` is
already in the devShell and `tools/import-yatai-assets.sh` in
mia-taiko-web is already the script that does this kind of copying.

**Every one of these goes into mia-taiko-web only.** The fork gets the
names added to `assets.js` and nothing else — the placeholder generator
from step 1 writes 1x1 stubs for them, so the public repo builds and runs
with the animation drawing nothing, and the private overlay supplies the
art. This is exactly the split step 1 built, and `check-no-assets.sh`
enforces it.

---

## Decisions I need from you

**1. Netplay and folders.** Three options, in order of my preference:

  a. **Send the path with the index.** `songsel` gains a `path` field; a
     peer receiving a path it is not in navigates there first, then
     applies the index. Peers stay in lockstep and folders work in
     netplay. Costs a protocol change and careful handling of the peer
     arriving mid-navigation.
  b. **Flatten during a session.** In netplay the wheel falls back to
     today's flat list, folders are unavailable. Simple, safe, and
     obviously worse to use.
  c. **Defer.** Ship folders for single player, leave netplay on the flat
     list, do (a) as its own piece of work later.

  I recommend (a), staged last so everything else is already working and
  tested when the protocol changes.

**2. Playlists.** Favourites generalise to them naturally: a playlist is a
named list of song ids, and favourites is the one called "Favourites".
I would build favourites *as* that, but only surface the favourites
folder in step 2, leaving user-created playlists as a later stage that
adds UI rather than data model. Say if you want the playlist UI in scope
now.

**3. Genre order and naming.** The 8 categories come from mongo with their
own order. Special folders (Favourites, Recent, Search, Random) need a
position — I would put Favourites first, then the genres, then Recent,
then the existing menu entries last, which is roughly YataiDON's layout.
Easy to change; say if you want something else.

---

## Stages

Each leaves the game working and is verifiable on its own. Every stage
that touches the client gets browser tests before it is called done.

### Stage 1 — a regression net, and two small fixes

**1.1 Browser tests for song select as it is today.**
The wheel renders, moving changes the selection, category jump moves by
category, entering a song opens difficulty select, escape comes back.
This is the net for everything after it, so it comes first.
*Verify:* tests pass against the current build.

**1.2 The three `disabled:` sites.**
songselect.js:2321, 2346 and 2404 grey out course-less entries during
netplay with `action !== "random"`, which is why Search still renders as
disabled after step 1 made it selectable. Same conjunct as the fix at
1617.
*Verify:* a test asserting Search is not disabled in a session.

**1.3 The P2 rainbow gauge.**
The `dy` ternary and the flip. Independent of everything else, so it goes
in early rather than waiting behind the song select work.
*Verify:* a test driving `drawGaugeRainbow` for both players and
comparing the drawn rectangle; visually against a two-player session.

### Stage 2 — the navigator, changing nothing

Introduce a `SongNavigator` owning `path`, `items` and `selectedIndex`,
and have `SongSelect` take its list from it. At this stage the root
listing is exactly today's list, in today's order.

Nothing changes on screen. This is the whole point: the risky move is
separating "what is in the wheel" from "how the wheel draws", and doing it
as a no-op means stage 1's tests prove it.
*Verify:* stage 1 tests pass unchanged; a test asserting the root listing
equals the old flat list item for item.

### Stage 3 — folders you can descend into

Folder and back-box item types. Root becomes: Favourites (empty for now),
the 8 genre folders, Recent, then the existing menu entries. Descending
replaces the listing, ascending restores it *with the cursor back on the
folder you came from* — YataiDON keeps `reopen_folder_path` and
`reopen_song_path` for exactly this and it matters a lot in use.

Netplay: folder entries are disabled during a session for now, which is
option (b) as a temporary measure regardless of what you choose for
decision 1.
*Verify:* tests for descend, ascend, cursor restoration, and that a song
inside a genre still loads and plays.

### Stage 4 — nesting from the song tree

`import.py` writes `folder` from the manifest's `rel`; `app.py` includes
it in `/api/songs`; the navigator nests within a genre when it is present.
Absent means flat, so this is safe against the current database and only
takes effect after a re-import.
*Verify:* re-import into the local mongo, check the OpenTaiko
collaborations appear as nested folders; check a database without the
field still renders genre-flat.

### Stage 5 — navigation feel

YataiDON's numbers, read out of `navigator.cpp` and `player.cpp`:

- one step per input, 166ms slide (`set_positions(snap, 166)`)
- an input arriving within **50ms** of the previous one becomes a **±10
  skip with no slide** (`current_ms <= last_moved + 50` → `skip_left/right`
  → `navigate(±10, snap=true)`). That is the acceleration model — a
  threshold, not a ramp.
- mouse wheel is one step
- entering difficulty select fans the other boxes off screen over 800ms,
  leaving restores over 500ms with a 166ms fade

Ours currently derives its timing from `this.songSelecting.speed`
(400 / the Song Select Speed setting) with a fourth-root multiplier on
larger moves. The setting stays and scales the new timing.
*Verify:* tests asserting the step duration, that a fast second input
produces a 10-step skip, and that the setting still scales it.

### Stage 6 — favourites

`db.favorites` keyed on `(username, song_id)`. `GET /api/favorites` and
`POST /api/favorites` following the shape of `/api/scores/*`, session
authenticated, CSRF protected. Client mirrors `scoreStorage`: server when
logged in, localStorage when not, no merge on login beyond taking the
server's copy.

Space toggles on the selected song, as in YataiDON. The Favourites folder
at the root lists them.
*Verify:* API tests against the local stack; browser tests for toggling,
persistence across reload, and the folder listing what was toggled. Logged
out and logged in both.

### Stage 7 — playlists

Only if you want the UI now. The data model lands in stage 6 either way.

### Stage 8 — netplay folder sync

Whichever of decision 1 you pick. If (a): `songsel` and `catjump` carry
the path, `onsongsel` navigates before applying the index, and folder
entries stop being disabled in a session.
*Verify:* two browser contexts in a real session, descending, selecting,
and confirming both land on the same song. The step 1 harness can drive
two pages, so this is testable end to end.

### Stage 9 — the ending animation

Drumsticks in, panel, confetti. Play the `se_game*` sounds that are
already loaded. Assets to mia-taiko-web, names into `assets.js`, real art
via the overlay.
*Verify:* the animation runs at the end of a song in the local stack with
the overlay image; the public build draws nothing and does not error.

### Stage 10 — the rainbow soul flame

8 frames from `tamashii_fire`, composited to a strip, drawn around the
soul glyph while the gauge is full.
*Verify:* as stage 9.

---

## Not in scope

Anything about the results screen beyond the ending animation, the option
menu, custom songs, the difficulty select layout, or the leaderboard.
The inherited asset history from step 1 (F2 in REFACTOR-PLAN.md) stays as
it is.
