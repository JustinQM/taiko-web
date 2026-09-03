# taiko-web

A web-based Taiko no Tatsujin simulator, played in the browser.

This is a fork. Most of what makes it good was taken from other projects,
so credit comes first.

---

## Credit

### YataiDON

Almost everything this fork changed about how the game feels came from
**[YataiDON](https://github.com/Yonokid/YataiDON)** by
[Yonokid](https://github.com/Yonokid) — a TJA player written in C++ with
[raylib](https://www.raylib.com/) and Lua-driven skins. GPL-3.0.

None of its code is here and none of it could be, since YataiDON is C++
and this is JavaScript on a canvas. What was taken is the design. Over
and over the question was "how does YataiDON do this?", and the answer
came out of its source before anything was written here.

These follow YataiDON directly:

- The song wheel's motion — moving the index at once, sliding boxes on an
  ease-out cubic, and opening the selected box as a longer animation that
  outlasts the slide
- The folder tree, including the back box repeated every ten songs
- Collection folders — Favorites and Recently Played resolve when opened,
  like YataiDON's `#COLLECTION` box.def folders
- The difficulty search, transcribed screen for screen: six boxes, the
  star level, the three-way confirmation prompt
- The background system — layered genre and fever backgrounds, Don-chan,
  the dancers, the chibi characters
- The animation primitives — fades, moves, resizes and their easing
- The ending animation and the rainbow soul gauge
- The modifier menu on the difficulty screen

YataiDON reads positions, spacing and timings out of its skin's
`texture.json`, `skin_config.json` and `animation.json` at runtime.
taiko-web has no equivalent, so those numbers are transcribed into the
source with a note saying where each came from. They're the skin's
numbers, not guesses.

If you want the real thing rather than a browser approximation, go use
YataiDON.

### Upstream

- **[Better-taiko-web](https://github.com/269Seahorse/Better-taiko-web)**
  by [269Seahorse](https://github.com/269Seahorse) — the fork this is
  based on. The search box and its filters (`oni:10`, `ura:1-5`,
  `gold:any`, `genre:namco`), song skipping, extra sounds and more.
- **[taiko-web](https://github.com/bui/taiko-web)** by
  [bui](https://github.com/bui) — the original and everything underneath:
  the engine, the TJA and osu parsers, accounts, netplay, custom song
  import.

---

## What this fork adds

### Song select

- **A folder tree.** Genres are folders, nested where a pack has structure
  on disk. Back box every ten songs, and an `N / total` counter.
- **Favorites**, toggled from the difficulty screen, in their own folder.
- **Recently played**, in the order you played them.
- **Difficulty search** — pick a course and a star level, get every chart
  in the library at exactly that level. The side panel counts how many
  there are and how many you've cleared and full comboed. The star range
  isn't fixed per course like YataiDON's; it goes as high as the library
  does.
- **Crowns on the wheel**, drawn from the skin.
- **You come back to the song you played**, in the folder it was in.
- **Back at the root stays in song select** instead of dropping to the
  title screen.

### Gameplay

- **The background is drawn on the canvas**, not the DOM: layered genre
  backgrounds, fever states, Don-chan, dancers, chibi characters. Fills
  the window at any aspect ratio, with a setting to hold it still.
- **The ending animation** and the **rainbow soul gauge flame**.
- **The results screen** — characters, confetti, and a donderful that
  looks like one.
- **Crowns and emblems from the skin** rather than hand-authored SVG, on
  the wheel, results and leaderboards.

### Settings

- **Three plugins absorbed as real settings**: song select speed, spartan
  mode, and skipping results in multiplayer.
- New settings for volume, resolution, still background, TJA title
  language, and a pad layout for controllers left in Nintendo mode.

### Netplay

- **Folder navigation is synced** — descending, backing out, jumping and
  the difficulty search picker all drive both clients together.

### Infrastructure

- The container image builds from this tree, with a local stack, a public
  dev stack and deploy scripts.
- A Playwright suite covering song select, folders, settings, netplay and
  backgrounds. The client is canvas and DOM with no build step, so a real
  browser is the only way to test it.
- Performance work: a frame-time harness, canvas caches for text and
  boxes, asset loading and decoding moved off the play path.

---

## Game assets

**This repository contains no game assets, deliberately.** The artwork,
audio and skin graphics are ripped from a commercial game.
`tools/check-no-assets.sh` guards against them turning up.

The client references images it doesn't ship and the loader treats a 404
as fatal, so blank placeholders are generated during the image build. The
game boots and draws nothing where they'd be. Supply your own by layering
them over the built image.

---

## Setup

See [Setup.md](Setup.md).
