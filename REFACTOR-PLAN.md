# Step 1 — move the deployment into the fork

Status: **approved 2026-09-02.** Tasks 1-15 done; task 16 stopped, see
below. Every task was verified as described unless noted.

## Where it ended up

Done, in commit order: jj colocation and ignores; the Dockerfile building
from the tree (tasks 7 and 8, pulled forward because the dev stack cannot
exist without it); the local stack; the seed script; the cookie flags; the
multiplayer bind; netplay Search; the analytics tag; the highscores
service; the production stack and scripts; the asset check; the move from
podman to Docker; generated asset placeholders; the browser test harness;
the SettingsView fix; all three plugins as settings; and the private repo
reduced to its asset layer.

Two things the plan did not anticipate, both found and fixed:

- **The fork did not boot.** assets.js requires 33 images upstream does
  not ship and treats any of them 404ing as fatal, so a clean clone
  stalled at 45%. Task 10's original check only looked at HTTP status
  codes, which passed while the game was dead. Placeholders are generated
  at image build now, and the browser tests would catch a regression.
- **A number setting crashed the settings screen.** SettingsView.getValue
  indexes a positional array by settings key, which only ever worked
  because plugin settings arrive as an array. Fixed with a lookup by id
  before task 13 could land.

## Task 16 -- stopped

Removing the plugin loader is larger than the plan assumed. It is 142
references across seven files, and the plan missed the one that matters:
importsongs.js has 25 of them, because dropping a folder of custom songs
into the browser also imports .taikoweb.js files from it, and that flow
re-enters itself with the number of plugins it started. Removing the
loader means restructuring the custom song import path, which is not
plugin infrastructure and is a feature that works.

The three plugins are absorbed and the loader is inert with PLUGINS = [],
so nothing depends on this. Options, in order of preference:

1. Stop loading plugins from config only -- drop PLUGINS from app.py and
   both config files, leave plugins.js and the import path alone. Kills
   the failure mode that motivated this (a config-listed plugin silently
   breaking when an upstream line moves, taking song select down) without
   touching custom song import. Perhaps 20 lines.
2. Full removal as planned, accepting the import path rework.
3. Leave it. Keeping upstream's code makes future merges quieter.

Goal: `taiko-web` becomes the whole application and its deployment, buildable
and runnable by anyone who clones it. `mia-taiko-web` shrinks to assets,
config and the song pipeline. Same behaviour, better structure.

---

## Findings that affect the plan

### F1 — the settings screen is DOM, not canvas. Absorbing the plugins is cheap.

`public/src/js/settings.js` is two classes. `Settings` holds a plain
`this.items` map (settings.js:13-64) plus localStorage load/validate.
`SettingsView` builds `<div class="setting-box">` elements into
`.view-content` (settings.js:307-383) — no canvas, no custom layout engine.
`.view-content` is `overflow-y: auto` (view.css:43-47) and keyboard
navigation already scrolls the selection into view (settings.js:786-800), so
extra rows cost nothing.

Adding one setting is three edits:

1. an entry in `Settings.init()`'s `this.items`
2. a `translations.settings.<key>` block in `strings.js` (only `en` is
   required — `separateStrings()` falls back to `en` per key, strings.js:1745)
3. one read at the consumption site

The generic types already cover every control the three plugins need:
`number` has `min`/`max`/`step`/`fixedPoint`/`format` (settings.js:344-371,
983-1020), `select` cycles `options` and labels them from
`strings.settings[name][value]` (settings.js:568, 637).

So: **not a big job — I recommend doing it in step 1**, roughly

| plugin | becomes | size |
|---|---|---|
| change-song-select-speed | `songSelectSpeed`, type `number` | ~30 lines |
| spartan-mode | `spartanGood`/`spartanOk`/`spartanBad`, type `select`, plus `Game.checkSpartanMode` | ~80 lines |
| skip-results-in-multiplayer | no setting; four direct edits in `scoresheet.js` | ~40 lines |

The third is the fiddliest — `toScoresShown` gains a `fromP2` parameter and
the sound playback reorders — but the plugin spells out the exact diff, so
it is transcription rather than design. Spartan mode's broken settings UI
disappears with the plugin: the bug is `strings[name]` where `name` is
`"good"`/`"ok"`/`"bad"` and `strings.good` does not exist.

Removing the plugin *loader* is a separate, larger deletion (plugins.js,
loader.js hooks, the plugins entry in song select, the `customSettings`
branches in settings.js). It is split into its own task below so a problem
there cannot taint the absorption, and it can be dropped from step 1 at no
cost to the rest.

### F2 — the fork already ships ripped assets, and always has.

The premise that upstream ships blank placeholders is only partly true.
Upstream blanked ~41 files (Don-chan animations, `taiko.png`,
`dancing-don.gif`, `vectors.json` paths). It left the rest in place. At the
pinned rev `a1c934d`, `git ls-files public/assets` is **245 tracked files**:

- ~60 real images — `bg_genre_*.png` (512x720, ~195 KB each),
  `notes_explosion.png` (888x1110), `difficulty.png`, the badge sheets,
  `results_tetsuohana2.png`
- 142 audio files, ~2.9 MB
- `public/assets/fonts/TnT.ttf` — 4.7 MB, name table reads
  `DFPKanTeiRyu-XB`, `(c) Copyright DynaComware Corp. 2002`,
  `Trademark by DynaComware Corp.` A commercial DynaFont, not a game rip,
  and redistributing it is its own problem
- `public/assets/fonts/Kozuka.otf`

These are in `origin/master` on a public GitHub repo now. **The split does
not achieve "nothing asset-related in the public repo" on its own**, and it
cannot — the exposure is inherited from upstream and lives in history that
predates the fork.

**Decided: leave them.** The exposure predates the fork and lives in
upstream's history, so the split cannot address it and step 1 will not try.
The reachable part of the goal is stopping *new* asset material entering,
which is task 12. Nothing of ours goes in.

### F3 — `tools/highscores/static/tnt.woff2` is a font subset.

12 KB Latin+digits subset of `TnT.ttf`, per the comment at style.css:14-17.
Under the stated rule it may not move into the fork as a binary. Since the
full `TnT.ttf` is already in the fork (F2) this makes no legal difference,
but keeping a binary out of git is tidier. **Decided:** task 9 generates it
at image build time with `fonttools`.

### F4 — three smaller things noticed in passing

- `songselect.js` has three more `action !== "random"` sites (2314, 2339,
  2397) that grey out course-less entries during netplay. Task 6 ports the
  1617 site exactly, so netplay search works but still renders as disabled
  in the wheel. **Decided: leave them** — that is step 2, with the rest of
  the song select work.
- `templates/index.html:5-12` hardcodes upstream's Google Analytics tag
  `G-ME8M5G343E`. **Decided: remove it** — task 8b below.
- `mia-taiko-web/assets/img/` contains `*.js.download` and `*.css` files
  from a saved-webpage dump; they are currently copied into the image.
  Not in scope; noted for task 11.

---

## Decisions I have assumed

State otherwise and I will change them.

- **`nginx.conf` lives in the fork.** The fork's `tools/nginx.conf`
  is a single-host config; mia's is the container one and is strictly
  better. The container version becomes the fork's, and `mia-taiko-web`
  drops its copy. (You listed nginx.conf under what mia keeps — this
  removes it. Easy to reverse.)
- **`assets/custom.js` moves to the fork** as `public/src/custom.js`. It is
  the browser half of the highscores service, it is code with no asset
  content, and it makes no sense apart from the service.
- **The fork's Dockerfile builds from the working tree** (`COPY . .`)
  instead of `git clone`. `build.sh` no longer takes an upstream rev.
- **`mia-taiko-web` keeps its own `docker-compose.yml`** rather than an
  override file, because it is pasted into Portainer by hand.

---

## Tasks

Dependency order. Each is one commit in one repo unless noted.

### Phase A — groundwork

**1. Colocate jj in the fork, add ignores.**
`jj git init --colocate` in `~/dev/taiko-web` (it is currently git-only).
Add to `.gitignore` before anything generates them: `.direnv/`, `result`,
`result-*`, `*.archive`, `*.dump`, `.env`, `docker-compose.override.yml`,
`public/src/plugins/`. `version.json` and `config.py` are already ignored.
Add `.dockerignore` covering `.git`, `.jj`, `.direnv`, `public/songs`,
`config.py`, `*.archive`.
*Verify:* `jj st` is clean and reports the same tree as `git status`.

**2. Local test stack, no seed yet.**
`docker-compose.dev.yml` in the fork: mongo, redis, app, multiplayer,
nginx, highscores, all on named volumes, no `/mnt/Data` bind mounts, ports
34900 (nginx) / 34901 / 34902 / 27117 / 6479 / 8100 — all free on this
machine. Add `podman-compose` and `mongodb-tools` to the flake devShell
(docker is present but the socket is root-only; `build.sh` already uses
podman). A local `config.py` from the example.
*Verify:* `podman-compose -f docker-compose.dev.yml up` and
`curl -s localhost:34900/api/config` returns JSON. Runs against the current
unmodified fork, so this task also proves the stack works before any patch
lands.

**3. Seed mongo from production.**
`ssh mia 'docker exec $(docker ps -qf name=taiko.*mongo) mongodump --db taiko --archive' > /tmp/taiko.archive`
then `mongorestore --archive` into the local mongo. Read-only against mia.
*Verify:* `curl -s localhost:34900/api/songs | jq length` ≈ 3369, and
`localhost:34900/highscores/` renders a board once task 9 lands.

### Phase B — the five patches, as source

Each is small and independently verifiable. Order does not matter within
the phase.

**4. `SESSION_COOKIE_SECURE` from config.**
`app.py:45` becomes `take_config('SESSION_COOKIE_SECURE')` defaulting to
`True` (note `take_config` returns `None` when absent, so the default must
be explicit — `None` would silently mean insecure). Document it in
`config.example.py`. Also wire `WTF_CSRF_SSL_STRICT` the same way: your
`config.py.example` sets it but nothing reads it today, so it is currently
a no-op.
*Verify:* stack up with `SESSION_COOKIE_SECURE = False`, register an
account over plain HTTP on :34900. With it unset, confirm the cookie is
`Secure` again.

**5. Multiplayer bind address from config.**
`server.py:...` `websockets.serve(connection, "localhost", port)` reads a
new `MULTIPLAYER_BIND` config value, default `"localhost"`. `server.py`
does not import config today, so the import is guarded and falls back to
the default when `config.py` is absent.
*Verify:* `curl -s -o /dev/null -w '%{http_code}' localhost:34900/p2` is
not 502; `ss -ltn` inside the container shows `0.0.0.0:34802`.

**6. Search reachable during netplay.**
`songselect.js:1617` — add `&& currentSong.action !== "search"`.
*Verify:* two browser sessions on :34900, start a netplay session, open
Search from song select. See F4 on the three sibling sites.

**7. Build tag in `version.json`.**
Move the inline Python out of the Dockerfile: `tools/get_version.sh` gains
an optional `BUILD_TAG` env var appended to `commit_short`. `build.sh`
sets it and runs the script before `podman build`; the Dockerfile copies
the resulting `version.json` rather than needing `.git`.
*Verify:* two builds of the same commit with different tags produce
different `?<tag>` query strings in `/` page source.

**8. nginx: drop Debian's default site.**
Moves verbatim into the fork's Dockerfile with its comment.
*Verify:* `nginx -T` in the container lists only our server block.

**8b. Remove upstream's Google Analytics tag.**
`templates/index.html:5-12` — delete the `googletagmanager.com` script tag
and the inline `gtag('config', 'G-ME8M5G343E')` block. Nothing else
references `gtag`.
*Verify:* `grep -ri gtag templates public` is empty; page loads with no
request to `googletagmanager.com` in the network log.

### Phase C — the deployment moves in

**9. Highscores service into the fork.**
`tools/highscores/` → `highscores/` in the fork, unchanged apart from:
`tnt.woff2` is generated at image build from
`public/assets/fonts/TnT.ttf` with `fonttools` (see F3) instead of being
committed; `assets/custom.js` → `public/src/custom.js`.
*Verify:* `localhost:34900/highscores/` renders against the seeded db;
`localhost:34900/` shows the leaderboard panel on a song.

**10. Dockerfile, compose, nginx, build/deploy into the fork.**
Fork gets: `Dockerfile` (builds from tree, no git clone, no asset COPYs, no
seds — everything is source now), `docker-compose.yml` (production shape,
build context `.`), `deploy/nginx.conf` (mia's container config),
`build.sh`, `deploy.sh`. Upstream's `tools/nginx.conf` and
`tools/supervisor.conf` stay put; they describe a non-container install.
*Verify:* from a clean clone of the fork into a temp dir,
`podman-compose build && up` serves a working (unstyled) game on a fresh
port. This is the "builds standalone for anyone who clones it" test.

**11. Shrink `mia-taiko-web`.**
Its `Dockerfile` becomes `FROM taiko-web:latest` plus the asset COPYs, the
vectors merge, the hitsound swap and the blank-PNG fallbacks — all the
asset work, none of the patches. Its `docker-compose.yml` points at the new
image name. `build.sh` builds the fork first, then the private layer.
Delete: `nginx.conf`, `assets/plugins/`, `assets/custom.js`,
`tools/highscores/`. Keep: `assets/`, `config.py.example`, `manifest.json`,
`tools/{scan,stage,import}.py`, `tools/deploy-songs.sh`,
`tools/import-yatai-*.sh`, `deploy.sh`. README rewritten to match.
*Verify:* full local stack from the two-stage build; then a real
`build.sh`/`deploy.sh` dry run streaming to mia **without** redeploying the
stack there — image load only, nothing restarted.

**12. Asset leak check.**
`tools/check-no-assets.sh` in the fork: fails if any file under
`public/assets/` differs from its blob at the pinned upstream rev, if
`public/src/plugins/` is non-empty, or if any new binary appears outside a
small allowlist. Wire it into `build.sh`.
*Verify:* it passes on the current tree, and fails if I drop one of mia's
PNGs into `public/assets/img/`.

### Phase D — the plugins (only if you agree with F1)

**13. Absorb `change-song-select-speed`.**
`songSelectSpeed` number setting, default 2.0, min 0.25, step 25,
fixedPoint 2, format `"%sx"`. `songselect.js:351` becomes
`speed: 400 / settings.getItem("songSelectSpeed")`.
*Verify:* change it in the settings screen, confirm the wheel rate changes
and survives a reload.

**14. Absorb `spartan-mode`.**
`Game.checkSpartanMode(score)` as a real method, called at game.js:244,
393 and 406. Three `select` settings — good / ok / bad — options
`continue`/`results`/`retry`/`back_to_select_song`, defaults
continue/continue/results, reusing the existing `pauseOptions` strings.
*Verify:* set bad→results, miss a note, confirm the song ends and the
result counts the remaining notes as bad; set ok→retry and confirm restart;
confirm it is inert in multiplayer and autoplay.

**15. Absorb `skip-results-in-multiplayer`.**
Four edits transcribed into `scoresheet.js`: the `init` p2 message branch
(81-88), the cursor at 423, `toScoresShown` gaining `fromP2` (151), and
`toSongsel` (158).
*Verify:* two sessions in netplay, finish a song, skip results from either
side, confirm both advance and the drum sound plays on the right channel.

**16. Remove the plugin loader.**
Delete `public/src/js/plugins.js`, its `<script>` tag, the `gameConfig.plugins`
block in loader.js:334-341, the plugins entry in song select and the
`customSettings` branches in settings.js. Drop `PLUGINS` from
`config.example.py` and from mia's `config.py.example`. Keep `CUSTOM_JS`.
*Verify:* stack boots with no console errors; settings screen and song
select both work. Note this makes future upstream merges noisier — it is
the one task here that can be skipped with no consequence to the rest.

---

## Not in scope

New features, redesign, song select navigation, the pre-existing asset
history (F2), the analytics tag (F4), deeper highscores integration, and
anything on mia beyond reading from it.
