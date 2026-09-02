# Step 2 — song select as a folder tree

Status: **approved 2026-09-02.** Executing.

Goal: replace the single flat wheel of 3367 songs with a navigable folder
tree modelled on YataiDON — genres at the top, favourites as their own
folder, YataiDON's navigation feel — plus three pieces of polish and one
real bug.

---

## What I found in our code

### The renderer is not the problem

`redraw()` is 1470 lines (songselect.js:1883-3350) and I expected it to be
the obstacle. It is not. It draws from exactly two things:

- `this.songs`, a flat array
- `this.selectedSong`, an index into it, wrapped with `this.mod()`

Everything else — the category bands, the crowns, the closed-song boxes,
the preview audio, the option menu — hangs off those. `this.songs` is
built once in `init()` (songselect.js:118-214): every song from
`assets.songs`, sorted by category, then the menu entries appended.

So the restructure is: **change what populates `this.songs`, not how it is
drawn.** A folder listing is a flat array too. Descending replaces the
array and resets the index; ascending restores them. The renderer never
needs to know there is a tree.

That is why stage 2 below is a deliberate no-op: introduce the navigator,
have it produce exactly today's list, prove nothing changed on screen.
Everything after that is comparatively cheap.

### The netplay protocol carries bare indices

`moveToSong` sends `p2.send("songsel", {song: <index>})`
(songselect.js:1547), `categoryJump` sends `catjump` with an index and a
direction (1593), and `onsongsel` (4161) applies them by index into
`this.songs`.

Those indices only mean the same thing if both peers hold the same list.
You want the two players never to diverge, so folder navigation has to
travel over the same channel: the messages gain the folder path, and a
peer that receives a path it is not in navigates there before applying the
index.

Until that lands, folder entries are simply refused during a session — so
neither peer can descend, both keep the identical root listing, and they
stay in lockstep by construction. That is a missing feature for one stage,
not a divergence.

### The whole tree is already client-side

`/api/songs` returns all 3367 songs at load, including `category`. The
tree is computed in the browser. Navigation needs no new API at all;
favourites are the only thing that needs the server.

### Recently Played has no data behind it

`db.scores` documents are `{username, hash, score}` — no timestamp. The
leaderboard's `hs_events` has timestamps but only records new records, not
every play, and it belongs to that service rather than the game.

So YataiDON's "15 Recently Played" cannot be built from what we store. It
needs a played-at timestamp, which `/api/scores/save` carries almost for
free since it already fires on every completed play. That is stage 7.

Existing scores have no timestamp and will not get one: nothing is
backfilled and nothing is synthesised, so the folder starts empty and
fills as songs are played.

---

## What I took from YataiDON

Read from `src/objects/song_select/file_navigator/` and `player.cpp`.

### The navigation model

`Navigator` holds a `current_path` and a flat `items` vector for **that
directory only** — not the whole tree. `load_current_directory(path)`
rebuilds it. A back box sits in the listing to ascend. This is the same
shape our `this.songs` already has, which is why it fits.

`reopen_folder_path` and `reopen_song_path` put the cursor back on the
song you came from when a folder is reopened. In use this matters far more
than it sounds.

### Root ordering

YataiDON orders by directory name, and the library uses numeric prefixes
to control it: genres `01`–`09`, then `11 Dan Dojo`, `13 Recommended`,
`14 Favorites`, `15 Recently Played`, `16 Difficulty Sort`, `17 New`,
`18 Search`. Its collection folders are declared by `#COLLECTION:` in
`box.def`, from the set `NEW, RECENT, FAVORITE, DIFFICULTY, RECOMMENDED,
SEARCH` (`src/objects/enums.h:143`).

Mirroring that, our root becomes:

1. the 8 genre folders, in `categories` id order (Pop, Anime, VOCALOID,
   Variety, Classical, Game Music, NAMCO Original, 創作譜面)
2. **Favorites**
3. **Recently Played**
4. **New** — songs by descending id, which is what our `order`/`id`
   already means
5. **Search** — our existing entry, moved into place
6. then taiko-web's own entries, which YataiDON has no equivalent for:
   Random, How to Play, About, Settings, Custom Songs

Dropped, with reasons: **Dan Dojo** (we have no dan mode), **Difficulty
Sort** (our search already filters by difficulty), **Recommended** (no
signal to base it on).

### The feel

- one step per input, **166ms** slide (`set_positions(snap, 166)`)
- an input arriving within **50ms** of the previous one becomes a
  **±10 skip with no slide** — `current_ms <= last_moved + 50` →
  `skip_left/right` → `navigate(±10, snap=true)`, `player.cpp:171-193`.
  That is the whole acceleration model: a threshold, not a ramp.
- mouse wheel is one step
- entering difficulty select fans the other boxes off screen over 800ms;
  leaving restores over 500ms with a 166ms fade
- **space toggles favourite** on the selected song (`player.cpp:195-201`)
- a don landing on the same frame as a navigation is dropped, with a
  comment explaining that it would otherwise open an item mid-slide

Ours derives its timing from `this.songSelecting.speed`
(`400 / songSelectSpeed`) with a fourth-root multiplier on larger moves.
The setting stays and scales the new timing.

---

## Favourites

Per-user, persisted, their own folder, toggled in-game. **Playlists are not
in scope**, but the data model has to carry them later without a
migration, so:

    db.playlists   { username, slug, name, songs: [id, ...], updated }

Favourites are the row with `slug: "favorites"`. A later playlist feature
adds rows and UI; it does not reshape anything. The alternative — a flat
`db.favorites` of `{username, song_id}` — would need migrating, so I am
not doing that.

API follows `/api/scores/*` exactly: session-authenticated, CSRF
protected, `GET /api/playlists/favorites` and `POST` to toggle. The client
mirrors `scoreStorage`: server when logged in, localStorage when not.

---

## The three polish items and the bug

- **Ending animation.** `se_gameclear.ogg`, `se_gamefail.ogg`,
  `se_gamefullcombo.ogg` and `se_gamedonderfulcombo.ogg` are listed in
  `assets.js:220-223` and referenced nowhere else in the codebase. There
  is no animation code at all.
- **Rainbow soul flame.** `draw.soul()` at view.js:552 and 650, no flame.
- **The P2 rainbow gauge bug, found.** `drawGaugeRainbow`
  (canvasdraw.js:1421) computes `var dy = config.multiplayer ? -8 : -8` —
  a ternary whose arms are identical. Someone meant to offset it for P2
  and never filled it in. The gauge body genuinely is drawn differently
  for P2 (`firstTop`/`secondTop` flip from 30/8 to 0/0, canvasdraw.js:1470,
  and the corners mirror), so the overlay lands wrong. Fix is the offset
  plus most likely a vertical flip; I will confirm the geometry against a
  running two-player session.

### Assets

`Skins/PyTaikoGreen` fetched fine from `ese.tjadataba.se`.
`Graphics/game/ending_anim/` has clear, full_combo, fail, their
highlights, `bachio_l/r_{in,fall,out}`, `fan_l/r`, `sparkle`, a 5-frame
`confetti/` directory and a `texture.json`.
`Graphics/game/gauge/tamashii_fire/` has the 8 frames.

Two are frame directories rather than sheets, so they get composited into
strips — `imagemagick` is in the devShell and
`mia-taiko-web/tools/import-yatai-assets.sh` is already the script that
does this kind of copying.

**All of it goes to mia-taiko-web.** The fork gets the names added to
`assets.js` and nothing else; the placeholder generator writes 1x1 stubs
so the public build runs with the animation drawing nothing, and the
private overlay supplies the art. `check-no-assets.sh` enforces it.

---

## One thing I found while setting up the local stack

`/api/preview` redirects to an absolute URL built from the `Host` header,
and nginx passes `$host`, which drops the port. On any deployment not on
port 80 the first play of each song 302s to a URL that does not resolve;
`make_preview` has already written the file by then, so `try_files` serves
it on the next attempt and the failure is invisible except as one silent
missing preview per song. It affects mia too (port 34800).

Fixed as its own commit before stage 1, since it is unrelated to song
select and affects the deployment as much as the local stack. All 3367
previews were pre-generated on the local stack anyway.

---

## Stages

Each leaves the game working. Every stage touching the client gets browser
tests before it is called done, run against the public stack on :34910;
the private stack on :34900 stays up throughout for you to look at.

### Stage 1 — a regression net, and two small fixes

**1.1 Browser tests for song select as it is today.** The wheel renders,
moving changes the selection, category jump moves by category, entering a
song opens difficulty select, escape returns. This is the net for
everything after it.

**1.2 The three `disabled:` sites.** songselect.js:2321, 2346 and 2404
grey out course-less entries in a session with `action !== "random"`,
which is why Search still renders as disabled after step 1 made it
selectable. Same conjunct as the fix at 1617.

**1.3 The P2 rainbow gauge.** Independent of the song select work, so it
goes early rather than waiting behind it.

### Stage 2 — the navigator, changing nothing

A `SongNavigator` owning `path`, `items` and `selectedIndex`, with
`SongSelect` taking its list from it. The root listing is exactly today's
list in today's order. Nothing changes on screen.
*Verify:* stage 1 tests pass unchanged; a test asserting the root listing
equals the old flat list item for item.

### Stage 3a — folders, single player

Folder and back-box item types, the root ordering above, descend and
ascend, cursor restoration on ascend. Genre folders from `category_id`.

Folder entries are refused during a netplay session, so both peers keep
the identical root listing and stay in lockstep.
*Verify:* descend, ascend, cursor restoration, a song inside a genre still
loads and plays; a session cannot descend and both peers agree.

### Stage 3b — folders in netplay

`songsel` and `catjump` carry the folder path; a peer receiving a path it
is not in navigates there first. Folder entry stops being refused.
*Verify:* two browser contexts in a real session — descend, ascend,
select, and confirm both land in the same folder on the same song. The
step 1 harness drives two pages, so this is testable end to end.

### Stage 4 — nesting below genre

`tools/scan.py` already records `rel`, the source-tree path, and
`tools/import.py` drops it. 3317 songs sit two levels deep, 50 three (the
OpenTaiko collaborations). `import.py` writes a `folder` field, `app.py`
serves it, the navigator nests within a genre when present. Absent means
flat, so the current database keeps working until you re-import.
*Verify:* re-import locally, check the collaborations nest; check a
database without the field still renders genre-flat.

### Stage 5 — navigation feel

The numbers above: 166ms step, the 50ms threshold to a ±10 snap skip,
wheel as one step, the fan-out timings. The Song Select Speed setting
scales it.
*Verify:* tests asserting step duration, that a fast second input produces
a 10-step skip, and that the setting still scales it.

### Stage 6 — favourites

`db.playlists` as above, the API, the client store, space to toggle, the
Favorites folder.
*Verify:* API tests against the local stack; browser tests for toggling,
persistence across reload, and the folder listing what was toggled — both
logged out and logged in.

### Stage 7 — Recently Played

A played-at timestamp written by `/api/scores/save`, and the folder,
ordered most recent first. Separate from stage 6 because it is a data
change rather than navigation work, and because it touches the score save
path that every completed play goes through.

Existing scores keep no timestamp — no backfill, no synthesised dates — so
the folder is empty until songs are played.
*Verify:* play a song on the local stack, confirm it appears at the top of
the folder; confirm scores predating the change are absent rather than
dated wrongly; confirm score saving still works for a logged-out user.

### Stage 8 — the ending animation

Drumsticks in, panel, confetti, and playing the `se_game*` sounds that are
already loaded and never used.
*Verify:* runs at the end of a song on the private stack; the public build
draws nothing and does not error.

### Stage 9 — the rainbow soul flame

8 frames composited to a strip, drawn around the soul glyph while the
gauge is full.
*Verify:* as stage 8.

---

## Not in scope

The results screen beyond the ending animation, the option menu, custom
songs, the difficulty select layout, the leaderboard, playlist UI, and the
inherited asset history from step 1.
