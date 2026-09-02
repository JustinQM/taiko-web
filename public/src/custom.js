/* Leaderboard panel for taiko-web.
 *
 * Injected into taiko-web's own page via the CUSTOM_JS config setting, so
 * it has to behave like a guest: every selector is scoped under #hs, every
 * class and id carries the hs- prefix, the custom properties live on #hs
 * rather than :root, and the one genuinely global thing a stylesheet can
 * declare -- an @font-face family -- is given a name nothing else will use.
 *
 * It deliberately duplicates the leaderboard's design tokens instead of
 * sharing them. /highscores/static/style.css can't be imported here without
 * dragging its whole cascade onto the game's DOM, so the values below are a
 * hand-kept copy. If the palette changes there, change it here too.
 *
 * Single file, no build step, no dependencies.
 */
(function () {
    "use strict";

    var API = "/highscores/api/song/";
    var PAGE = "/highscores/";

    var root, head, body, label;
    var song = null;
    var open = false;
    var loadedFor = null;

    var DIFF_ORDER = ["easy", "normal", "hard", "oni", "ura"];
    // only needed when the API is unreachable and we render a board of our own
    var DIFF_LABEL = { easy: "Easy", normal: "Normal", hard: "Hard",
                       oni: "Extreme", ura: "Inner Extreme" };
    var DIFF_COLOR = { easy: "#f76c1f", normal: "#8fbf3f", hard: "#5b8fd4",
                       oni: "#c8386e", ura: "#7a3fb8" };

    // -------------------------------------------------------------- touch

    /* taiko-web binds touchstart/touchmove/touchend on document.documentElement
       and preventDefaults them (main.js), which cancels the synthetic click a
       normal click handler waits for -- so on a handheld a tap on the panel
       never became a click at all, even though the element was hit-testable.
       Handle touchend directly instead, and keep the click path for desktop
       behind a guard against the ghost click a tap can still emit. */
    var lastTap = 0;

    function tappable(el, fn) {
        var x = 0, y = 0, moved = false;

        el.addEventListener("touchstart", function (e) {
            var t = e.changedTouches && e.changedTouches[0];
            if (!t) return;
            x = t.clientX; y = t.clientY; moved = false;
        });
        el.addEventListener("touchmove", function (e) {
            var t = e.changedTouches && e.changedTouches[0];
            if (!t) return;
            // a drag is someone scrolling the list, not choosing something
            if (Math.abs(t.clientX - x) > 10 || Math.abs(t.clientY - y) > 10) {
                moved = true;
            }
        });
        el.addEventListener("touchend", function (e) {
            e.stopPropagation();               // don't let it read as a drum hit
            if (moved) return;
            if (e.cancelable) e.preventDefault();   // suppress the ghost click
            lastTap = Date.now();
            fn(e);
        });
        el.addEventListener("click", function (e) {
            if (Date.now() - lastTap < 700) return; // already handled as a tap
            fn(e);
        });
    }

    /* Keep touches inside the panel away from the game. Propagation only:
       preventDefault here would kill the native scrolling of the expanded
       list, which is exactly what we are trying to keep. */
    function stopTouch(el) {
        ["touchstart", "touchmove", "touchend"].forEach(function (n) {
            el.addEventListener(n, function (e) { e.stopPropagation(); });
        });
    }

    /* The tap's click never fires, so default navigation never happens.
       Open explicitly -- still inside the gesture, so it is not treated as
       a popup.

       The window is named so repeat opens reuse the same tab instead of
       piling up a new one per tap. A named target and noopener are
       mutually exclusive (noopener always forces a fresh context), and the
       target is our own same-origin leaderboard, so handing it an opener
       reference costs nothing. */
    var LEADERBOARD_TAB = "taikoLeaderboard";

    function openLink(href) {
        if (!href) return;
        try {
            var w = window.open(href, LEADERBOARD_TAB);
            if (w && w.focus) w.focus();
        } catch (e) {
            window.open(href, LEADERBOARD_TAB);
        }
    }

    // ---------------------------------------------------------- fullscreen

    /* The panel sits on top of taiko-web's own fullscreen control, so this
       replaces it in the opposite corner. It goes through the game's
       toggleFullscreen()/fullScreenSupported globals rather than the raw
       Fullscreen API, which keeps the vendor-prefix handling in one place.
       main.js may not have run when we build, so the check is retried from
       the same interval that already watches for gameplay. */
    var fsBtn = null;
    var fsResolved = false;

    var FS_ICON =
        '<svg viewBox="0 0 24 24" aria-hidden="true">' +
        '<path class="hs-fs-out" d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>' +
        '<path class="hs-fs-in" d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/>' +
        '</svg>';

    function syncFsIcon() {
        if (!fsBtn) return;
        var on = !!(document.fullscreenElement ||
                    document.webkitFullscreenElement ||
                    document.mozFullScreenElement);
        fsBtn.classList.toggle("on", on);
        fsBtn.title = on ? "Exit fullscreen" : "Fullscreen";
        fsBtn.setAttribute("aria-label", fsBtn.title);
    }

    /* main.js may not have run yet, and there is no longer an interval to
       piggyback on, so retry briefly and then stop. */
    var fsTries = 0;

    function pollFullscreen() {
        ensureFullscreen();
        if (!fsResolved && fsTries++ < 25) setTimeout(pollFullscreen, 200);
    }

    function ensureFullscreen() {
        if (fsResolved || !document.body) return;
        // undefined means main.js has not defined it yet; false means no.
        if (typeof window.fullScreenSupported === "undefined") return;
        fsResolved = true;
        if (!window.fullScreenSupported) return;

        fsBtn = document.createElement("div");
        fsBtn.id = "hs-fs";
        fsBtn.setAttribute("role", "button");
        fsBtn.tabIndex = 0;
        fsBtn.innerHTML = FS_ICON;
        document.body.appendChild(fsBtn);

        stopTouch(fsBtn);
        tappable(fsBtn, function () {
            if (typeof window.toggleFullscreen === "function") {
                window.toggleFullscreen();
            }
        });
        fsBtn.addEventListener("keydown", function (e) { e.stopPropagation(); });

        ["fullscreenchange", "webkitfullscreenchange", "mozfullscreenchange"]
            .forEach(function (n) { document.addEventListener(n, syncFsIcon); });

        syncFsIcon();
        // match whatever the panel is doing right now
        if (root) fsBtn.classList.toggle("hidden", root.classList.contains("hidden"));
    }

    // ---------------------------------------------------------------- ui

    /* The crown and the star are the game's own vector paths, lifted from
       assets/vectors-patch.json -- the same ones the leaderboard inlines.
       The crown's gradient stops and its stroke-then-fill order come from
       canvasdraw.js, which is why paint-order:stroke appears below: the
       game strokes the outline first and fills over it, so an 18px black
       edge never eats into the metal. */
    var SPRITE =
        '<svg id="hs-sprite" aria-hidden="true" focusable="false">' +
        '<defs>' +
        '<linearGradient id="hs-g-gold" x1="0" y1="0" x2="1" y2="0">' +
        '<stop offset="0" stop-color="#ffffc5"/><stop offset=".23" stop-color="#ffff44"/>' +
        '<stop offset=".53" stop-color="#efbd12"/><stop offset=".83" stop-color="#ffff44"/>' +
        '<stop offset="1" stop-color="#efbd12"/></linearGradient>' +
        '<linearGradient id="hs-g-silver" x1="0" y1="0" x2="1" y2="0">' +
        '<stop offset="0" stop-color="#d6efef"/><stop offset=".23" stop-color="#bddfde"/>' +
        '<stop offset=".53" stop-color="#97c1c0"/><stop offset=".83" stop-color="#bddfde"/>' +
        '<stop offset="1" stop-color="#97c1c0"/></linearGradient>' +
        '<linearGradient id="hs-g-rainbow" x1="0" y1="0" x2="1" y2=".4">' +
        '<stop offset="0" stop-color="#ff5bb0"/><stop offset=".18" stop-color="#ff8a3d"/>' +
        '<stop offset=".36" stop-color="#ffe74d"/><stop offset=".54" stop-color="#6ce86c"/>' +
        '<stop offset=".72" stop-color="#4fc9ff"/><stop offset=".9" stop-color="#a97bff"/>' +
        '<stop offset="1" stop-color="#ff5bb0"/></linearGradient>' +
        '<symbol id="hs-i-crown" viewBox="-16 -16 126 106">' +
        '<path d="M8 74 L0 14 L25 38 L47 0 L69 38 L94 14 L86 74 Z" stroke="#000"' +
        ' stroke-width="18" stroke-linejoin="miter" stroke-miterlimit="1.7"/></symbol>' +
        '<symbol id="hs-i-star" viewBox="0 0 19 18.4">' +
        '<path d="M9.5 0 L12.24 6.36 L19 7.05 L13.9 11.65 L15.38 18.4 L9.5 14.85' +
        ' L3.62 18.4 L5.1 11.65 L0 7.05 L6.76 6.36 Z"/></symbol>' +
        '</defs></svg>';

    var CSS = [
        /* The leaderboard's display face. Its 12KB Latin+digit subset sits on
           this same origin; the game's full 4.7MB TnT.ttf is the fallback, far
           too heavy to pull mid-session but correct if the subset ever moves.
           The family name is deliberately odd so it cannot collide with any
           face taiko-web declares. */
        '@font-face{font-family:"HsTnT";font-display:swap;',
        ' src:url("/highscores/static/tnt.woff2") format("woff2"),',
        '     url("/assets/fonts/TnT.ttf") format("truetype")}',

        /* --- tokens, copied from tools/highscores/static/style.css --------- */
        '#hs,#hs-fs{--bg:#141019;--panel:#221c2b;--panel-2:#2b2436;--panel-3:#342c41;',
        ' --line:#3a3147;--line-2:#4b4059;',
        ' --ink:#f4f0f8;--ink-2:#bcb2ca;--ink-3:#897e9b;',
        ' --accent:#ff5716;--accent-2:#ffb02e;--pink:#f72568;',
        ' --j-good:#4aa8ff;--j-ok:#ffc93c;--j-bad:#ff4d5e;',
        ' --gold:#ffd12e;--silver:#cfe0e0;--bronze:#d98b4a;',
        ' --sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,',
        '        "Helvetica Neue",Arial,"Noto Sans JP",sans-serif;',
        ' --disp:"HsTnT",var(--sans)}',

        /* --- shell --------------------------------------------------------- */
        '#hs{position:fixed;right:12px;top:12px;z-index:9999;',
        ' width:auto;max-width:min(390px,46vw);',
        ' font:13px/1.45 var(--sans);color:var(--ink);',
        ' font-variant-numeric:tabular-nums;text-align:left;',
        ' background:rgba(20,16,25,.9);border:1px solid var(--line);',
        ' border-radius:10px;backdrop-filter:blur(14px);overflow:hidden;',
        ' transition:opacity .2s;box-shadow:0 10px 30px -12px #000;',
        ' -webkit-tap-highlight-color:transparent}',
        '#hs.hidden{opacity:0;pointer-events:none}',
        '#hs *{box-sizing:border-box}',
        '#hs a{text-decoration:none;color:inherit}',
        '#hs-sprite{position:absolute;width:0;height:0;overflow:hidden}',

        /* the drum's colors, the same rule that sits under the site header */
        '#hs::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;',
        ' background:linear-gradient(90deg,var(--accent),var(--accent-2) 34%,',
        ' #5fb7c1 67%,var(--pink))}',

        /* --- header -------------------------------------------------------- */
        '#hs-head{display:flex;align-items:center;gap:8px;padding:8px 11px;',
        ' cursor:pointer;user-select:none;',
        ' background:linear-gradient(180deg,var(--panel-2),var(--panel))}',
        '#hs-head:hover{background:var(--panel-2)}',
        /* taiko.png is a 138x810 strip; the drum is its top 162px */
        '#hs-drum{width:19px;flex:none;aspect-ratio:138/162;',
        ' background:url("/assets/img/taiko.png") no-repeat 0 0/100% auto;',
        ' filter:drop-shadow(0 1px 3px rgba(0,0,0,.6))}',
        '#hs-label{flex:1;min-width:0;font:400 15px/1.2 var(--disp);',
        ' letter-spacing:.01em;white-space:nowrap;overflow:hidden;',
        ' text-overflow:ellipsis}',
        '#hs-open{flex:none;font:600 10px/1 var(--sans);letter-spacing:.1em;',
        ' text-transform:uppercase;color:var(--accent-2);padding:4px 7px;',
        ' border:1px solid color-mix(in srgb,var(--accent) 45%,transparent);',
        ' border-radius:999px}',
        '#hs-open:hover{background:color-mix(in srgb,var(--accent) 18%,transparent)}',
        '#hs-caret{flex:none;color:var(--ink-3);font-size:9px;transition:transform .15s}',
        '#hs.open #hs-caret{transform:rotate(180deg)}',

        '#hs-body{display:none;max-height:min(70vh,520px);overflow-y:auto;',
        ' border-top:1px solid var(--line);padding-bottom:2px;',
        ' scrollbar-width:thin;scrollbar-color:var(--line-2) transparent}',
        '#hs.open #hs-body{display:block}',
        '#hs-body::-webkit-scrollbar{width:8px}',
        '#hs-body::-webkit-scrollbar-thumb{background:var(--line-2);border-radius:4px}',

        /* --- one difficulty block ------------------------------------------ */
        '#hs .hs-d{padding:7px 11px 8px}',
        '#hs .hs-d+.hs-d{border-top:1px solid ',
        ' color-mix(in srgb,var(--line) 60%,transparent)}',
        '#hs .hs-dh{display:flex;align-items:center;gap:6px;margin-bottom:5px}',

        /* difficulty badge: difficulty.png is 168x720, five 168x144 cells */
        '#hs .hs-diff{display:inline-flex;align-items:center;gap:5px;',
        ' padding:2px 8px 2px 4px;border-radius:999px;',
        ' font:700 10.5px/1.5 var(--sans);letter-spacing:.02em;white-space:nowrap;',
        ' color:color-mix(in srgb,var(--c) 45%,#fff);',
        ' background:color-mix(in srgb,var(--c) 20%,transparent);',
        ' box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--c) 40%,transparent)}',
        '#hs .hs-di{width:15px;flex:none;aspect-ratio:7/6;',
        ' background:url("/assets/img/difficulty.png") no-repeat 0 0/100% 500%}',
        '#hs .hs-di.easy{background-position:0 0}',
        '#hs .hs-di.normal{background-position:0 25%}',
        '#hs .hs-di.hard{background-position:0 50%}',
        '#hs .hs-di.oni{background-position:0 75%}',
        '#hs .hs-di.ura{background-position:0 100%}',

        '#hs .hs-stars{display:inline-flex;gap:1px}',
        '#hs .hs-stars svg{width:8px;height:8px;flex:none;fill:var(--pink)}',
        '#hs .hs-n{margin-left:auto;flex:none;color:var(--ink-3);',
        ' font:600 9.5px/1 var(--sans);letter-spacing:.08em;text-transform:uppercase}',

        /* --- one score row -------------------------------------------------- */
        '#hs .hs-row{display:grid;grid-template-columns:auto minmax(0,1fr) auto;',
        ' column-gap:7px;row-gap:1px;align-items:center;padding:3px 0}',
        '#hs .hs-row+.hs-row{border-top:1px solid ',
        ' color-mix(in srgb,var(--line) 35%,transparent)}',
        '#hs .hs-rank{grid-area:1/1/3/2;display:inline-flex;align-items:center;',
        ' justify-content:center;min-width:19px;height:18px;padding:0 4px;',
        ' border-radius:5px;font:600 10.5px/1 var(--sans);',
        ' color:var(--ink-2);background:var(--panel-3)}',
        '#hs .hs-rank.hs-r1{color:#3a2600;background:linear-gradient(180deg,#ffe270,var(--gold));',
        ' box-shadow:0 2px 7px -3px var(--gold)}',
        '#hs .hs-rank.hs-r2{color:#22303a;background:linear-gradient(180deg,#eef7f7,var(--silver))}',
        '#hs .hs-rank.hs-r3{color:#2e1706;background:linear-gradient(180deg,#f0ad6f,var(--bronze))}',
        '#hs .hs-user{grid-area:1/2;display:flex;align-items:center;gap:5px;',
        ' min-width:0;font-weight:600;font-size:12px}',
        '#hs .hs-user span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
        '#hs a.hs-user:hover span{color:var(--accent-2);text-decoration:underline}',
        '#hs .hs-pts{grid-area:1/3;font:400 13px/1 var(--disp);text-align:right;',
        ' white-space:nowrap}',
        '#hs .hs-meta{grid-area:2/2/3/4;display:flex;align-items:center;gap:6px;',
        ' font-size:10.5px;color:var(--ink-3);white-space:nowrap;overflow:hidden}',
        '#hs .hs-acc{font-weight:600;color:var(--ink-2)}',
        /* Good/OK/Bad keep their own colors rather than collapsing into accuracy */
        '#hs .hs-jd{font-weight:600}',
        '#hs .hs-jd.good{color:var(--j-good)}',
        '#hs .hs-jd.ok{color:var(--j-ok)}',
        '#hs .hs-jd.bad{color:var(--j-bad)}',
        '#hs .hs-jd.hs-zero{color:var(--ink-3);font-weight:400}',
        '#hs .hs-sep{color:var(--line-2)}',
        '#hs .hs-combo{margin-left:auto;flex:none}',

        /* the game strokes the crown then fills over it; paint-order matches */
        '#hs .hs-crown{width:13px;height:11px;flex:none;paint-order:stroke;',
        ' filter:drop-shadow(0 1px 1px rgba(0,0,0,.6))}',
        '#hs .hs-crown.silver{fill:url(#hs-g-silver)}',
        '#hs .hs-crown.gold{fill:url(#hs-g-gold)}',
        '#hs .hs-crown.rainbow{fill:url(#hs-g-rainbow)}',

        /* --- results screen ------------------------------------------------
           The difficulty just played, and the player's own row in it. */
        '#hs .hs-d.hs-played{background:color-mix(in srgb,var(--accent) 8%,transparent);',
        ' box-shadow:inset 3px 0 0 var(--accent)}',
        /* Bleed the highlight out symmetrically: padding cancels the
           negative margin on both sides, so the columns stay lined up
           with every other row instead of looking indented. */
        '#hs .hs-row.hs-me{margin:2px -7px;padding:4px 7px;border-radius:7px;',
        ' border-top:0;background:color-mix(in srgb,var(--accent) 16%,transparent);',
        ' box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 38%,transparent)}',
        '#hs .hs-row.hs-me+.hs-row{border-top:0}',
        '#hs .hs-row.hs-me.hs-first{background:color-mix(in srgb,var(--gold) 18%,transparent);',
        ' box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--gold) 45%,transparent)}',

        /* the run just played, shown next to whatever is on the board */
        '#hs .hs-row.hs-cmp{border-top:0;padding-top:1px}',
        '#hs .hs-cmplabel{font:700 8.5px/1 var(--sans);letter-spacing:.09em;',
        ' text-transform:uppercase;color:var(--ink-3);flex:none}',
        '#hs .hs-delta{font:700 10.5px/1 var(--sans);flex:none}',
        '#hs .hs-delta.hs-up{color:var(--accent-2)}',
        '#hs .hs-delta.hs-down{color:var(--ink-3)}',
        '#hs .hs-row.hs-cmp .hs-pts{font-size:12px;color:var(--ink-2)}',
        '#hs .hs-row.hs-cmp .hs-user{gap:6px}',
        '#hs .hs-badge{flex:none;font:700 8.5px/1 var(--sans);letter-spacing:.09em;',
        ' text-transform:uppercase;padding:3px 6px;border-radius:999px;white-space:nowrap}',
        '#hs .hs-badge.hs-first{color:#3a2600;',
        ' background:linear-gradient(180deg,#ffe270,var(--gold));',
        ' box-shadow:0 2px 8px -3px var(--gold)}',
        '#hs .hs-badge.hs-best{color:#2a1000;',
        ' background:linear-gradient(180deg,var(--accent-2),var(--accent))}',
        '#hs .hs-badge.hs-pending{color:var(--ink-3);background:transparent;',
        ' box-shadow:inset 0 0 0 1px var(--line-2)}',

        '#hs .hs-empty{color:var(--ink-3);font-size:11px;padding:3px 0}',
        '#hs .hs-msg{padding:12px 11px;color:var(--ink-3);font-size:12px}',

        /* --- fullscreen button --------------------------------------------
           A separate control in the opposite corner, not part of the panel:
           the panel covers taiko-web's own fullscreen button in the top
           right. Same shell treatment so the two read as a set. */
        '#hs-fs{position:fixed;right:12px;bottom:12px;z-index:9999;',
        ' width:40px;height:40px;display:flex;align-items:center;',
        ' justify-content:center;border-radius:10px;cursor:pointer;',
        ' color:var(--ink-2);background:rgba(20,16,25,.9);',
        ' border:1px solid var(--line);backdrop-filter:blur(14px);',
        ' box-shadow:0 10px 30px -12px #000;-webkit-tap-highlight-color:transparent;',
        ' transition:opacity .2s,color .15s,border-color .15s,background .15s}',
        '#hs-fs.hidden{opacity:0;pointer-events:none}',
        '#hs-fs:hover{color:var(--ink);border-color:var(--line-2);',
        ' background:var(--panel-2)}',
        '#hs-fs:active{color:var(--accent-2)}',
        '#hs-fs svg{width:20px;height:20px;fill:none;stroke:currentColor;',
        ' stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}',
        '#hs-fs .hs-fs-in{display:none}',
        '#hs-fs.on .hs-fs-out{display:none}',
        '#hs-fs.on .hs-fs-in{display:block}',

        '@media(max-width:700px){#hs{max-width:66vw;font-size:12px}}'
    ].join("\n");

    function build() {
        if (root) return;

        var css = document.createElement("style");
        css.id = "hs-style";
        css.textContent = CSS;
        document.head.appendChild(css);

        root = document.createElement("div");
        root.id = "hs";
        root.innerHTML =
            SPRITE +
            '<div id="hs-head">' +
            '  <span id="hs-drum"></span>' +
            '  <span id="hs-label">Leaderboards</span>' +
            '  <a id="hs-open" target="taikoLeaderboard">open</a>' +
            '  <span id="hs-caret">▼</span>' +
            '</div>' +
            '<div id="hs-body"></div>';
        document.body.appendChild(root);

        head = root.querySelector("#hs-head");
        body = root.querySelector("#hs-body");
        label = root.querySelector("#hs-label");

        stopTouch(root);
        // Delegated, so score rows rendered later need no extra wiring.
        tappable(root, function (e) {
            var t = e.target;
            if (!t || !t.closest) return;
            var link = t.closest("#hs a[href]");
            if (link) {
                openLink(link.getAttribute("href"));
            } else if (t.closest("#hs-head")) {
                toggle();
            }
        });

        // The game listens on window for keys; don't let the panel steal them.
        root.addEventListener("keydown", function (e) { e.stopPropagation(); });

        paint();
        pollFullscreen();
    }

    function setOpen(v) {
        open = v;
        root.classList.toggle("open", open);
    }

    function toggle() {
        setOpen(!open);
        if (open) load();
    }

    function paint() {
        if (!root) return;
        var link = root.querySelector("#hs-open");
        if (song) {
            label.textContent = song.title;
            link.href = PAGE + "song/" + song.id;
        } else {
            label.textContent = "Leaderboards";
            link.href = PAGE;
        }
        if (open) load();
    }

    // -------------------------------------------------------------- data

    function load() {
        if (!song) {
            body.innerHTML = '<div class="hs-msg">Pick a song to see its scores.</div>';
            loadedFor = null;
            return;
        }
        if (loadedFor === song.id) return;
        loadedFor = song.id;
        body.innerHTML = '<div class="hs-msg">Loading…</div>';

        fetch(API + song.id + "?limit=5")
            .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
            .then(function (d) {
                if (loadedFor !== d.id) return;
                render(d);
            })
            .catch(function () {
                if (loadedFor === song.id) {
                    body.innerHTML = '<div class="hs-msg">No scores for this song yet.</div>';
                }
            });
    }

    function esc(s) {
        return String(s).replace(/[&<>"]/g, function (c) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
        });
    }

    // ------------------------------------------------------------ pieces

    function crown(kind) {
        if (!kind) return "";
        return '<svg class="hs-crown ' + esc(kind) + '" aria-hidden="true">' +
               '<use href="#hs-i-crown"/></svg>';
    }

    function stars(n) {
        n = Math.max(0, Math.min(n | 0, 10));
        if (!n) return "";
        var out = '<span class="hs-stars" title="' + n + '★">';
        for (var i = 0; i < n; i++) {
            out += '<svg viewBox="0 0 19 18.4"><use href="#hs-i-star"/></svg>';
        }
        return out + "</span>";
    }

    function diffBadge(key, label, color) {
        return '<span class="hs-diff" style="--c:' + esc(color) + '">' +
               '<i class="hs-di ' + esc(key) + '"></i>' + esc(label) + '</span>';
    }

    function judgment(r) {
        function n(v, cls) {
            return '<span class="hs-jd ' + cls + (v ? "" : " hs-zero") + '">' +
                   (v || 0) + '</span>';
        }
        return n(r.good, "good") + '<i class="hs-sep">/</i>' +
               n(r.ok, "ok") + '<i class="hs-sep">/</i>' +
               n(r.bad, "bad");
    }

    function row(r, k, mark) {
        var mine = !!(mark && k === mark.diff && r.user === mark.user);
        var rank = r.rank < 4 ? " hs-r" + r.rank : "";
        // Only badge the row once the new score is actually the one shown;
        // before that this row is still their previous entry.
        var won = mine && mark.landed;
        var cls = "hs-row" + (mine ? " hs-me" : "") +
                  (won && r.rank === 1 ? " hs-first" : "");
        var badge = "";
        if (won) {
            if (r.rank === 1) {
                badge = '<span class="hs-badge hs-first">1st place</span>';
            } else if (mark.improved) {
                badge = '<span class="hs-badge hs-best">New best</span>';
            }
        }
        var out = '<div class="' + cls + '">';
        out += '<span class="hs-rank' + rank + '">' + r.rank + '</span>';
        out += '<a class="hs-user" href="' + PAGE + "user/" +
               encodeURIComponent(r.user) + '" target="' + LEADERBOARD_TAB + '"' +
               ' title="' + esc(r.user) + '’s profile">' +
               '<span>' + esc(r.user) + '</span>' + crown(r.crown) + '</a>';
        out += '<span class="hs-pts">' + r.points.toLocaleString() + '</span>';
        out += '<span class="hs-meta">' + badge +
               '<span class="hs-acc">' + r.accuracy.toFixed(1) + '%</span>' +
               judgment(r) +
               (r.maxCombo ? '<span class="hs-combo">' +
                             r.maxCombo.toLocaleString() + ' combo</span>' : "") +
               '</span>';
        return out + '</div>';
    }

    function render(d, mark) {
        var html = "";

        DIFF_ORDER.forEach(function (k) {
            var b = d.boards[k];
            if (!b) return;
            var rows = b.rows;
            html += '<div class="hs-d' +
                    (mark && k === mark.diff ? " hs-played" : "") + '">';
            html += '<div class="hs-dh">' +
                    diffBadge(k, b.label, b.color) +
                    stars(b.stars) +
                    '<span class="hs-n">' + b.players +
                    (b.players === 1 ? " player" : " players") + '</span>' +
                    '</div>';

            var played = mark && k === mark.diff;
            var placed = false;
            if (!rows.length && !played) {
                html += '<div class="hs-empty">Unclaimed</div>';
            } else {
                rows.forEach(function (r) {
                    html += row(r, k, mark);
                    // the comparison belongs directly under their own row
                    if (played && r.user === mark.user) {
                        html += compareRow(mark);
                        placed = true;
                    }
                });
                // no entry of theirs on this board yet
                if (played && !placed) html += compareRow(mark);
            }
            html += '</div>';
        });

        body.innerHTML = html || '<div class="hs-msg">No scores for this song yet.</div>';

        if (mark) {
            var blk = body.querySelector(".hs-d.hs-played");
            // scroll the panel's own list, never the page behind it
            if (blk) body.scrollTop = Math.max(0, blk.offsetTop - body.offsetTop - 4);
        }
    }

    // ------------------------------------------------------------ results

    /* The leaderboard's poller only sweeps the scores collection every
       POLL_SECONDS (60 by default), so straight after a song the API will
       usually still be serving the previous standings. Rather than lower
       that interval, the panel tolerates the lag: it refetches a few times
       over the first several seconds, and until the new score shows up it
       splices the player's own result -- taken from the scoresheet event --
       into the board as a provisional row at the rank it will land in. */
    var RESULT_RETRIES = [0, 2500, 5000, 9000, 14000];
    var resultRun = 0;

    function num(v) {
        var n = parseInt(v, 10);
        return isNaN(n) ? 0 : n;
    }

    function playerName() {
        var a = window.account;
        return (a && a.loggedIn && a.username) ? a.username : null;
    }

    /* Only the combo crowns can be derived from the results payload: it
       carries the gauge but not the clear threshold, so a silver crown
       would be a guess. The real one arrives with the row itself. */
    function crownFor(good, ok, bad) {
        if (bad) return "";
        return ok ? "gold" : "rainbow";
    }

    function money(n) { return n.toLocaleString(); }

    /* The run just played, shown alongside whatever the board holds, so
       the two are always comparable. Until the new score lands this is the
       run itself; once it has landed the board row IS the run, so the
       comparison flips to the score it replaced. Either way both numbers
       are on screen.

       taiko-web never overwrites a better score, so a run that loses to
       the existing entry will never appear on the board -- it still gets
       shown here rather than being dropped or left spinning as pending. */
    function compareRow(mark) {
        var prev = mark.previousRow;
        var showing = mark.landed ? prev : mark.run;
        if (!showing) return "";

        var label = mark.landed ? "Previous" : "This run";
        var delta = prev ? mark.points - prev.points : null;
        var bits = '<span class="hs-cmplabel">' + label + "</span>";

        if (delta !== null && delta !== 0) {
            bits += '<span class="hs-delta ' + (delta > 0 ? "hs-up" : "hs-down") + '">' +
                    (delta > 0 ? "+" : "\u2212") + money(Math.abs(delta)) + "</span>";
        } else if (!prev) {
            bits += '<span class="hs-cmplabel">first score</span>';
        }
        if (!mark.landed && mark.willLand) {
            bits += '<span class="hs-badge hs-pending">Pending</span>';
        }

        var total = showing.good + showing.ok + showing.bad;
        var out = '<div class="hs-row hs-cmp">';
        out += '<span class="hs-user">' + bits + "</span>";
        out += '<span class="hs-pts">' + money(showing.points) + "</span>";
        out += '<span class="hs-meta">' +
               '<span class="hs-acc">' + showing.accuracy.toFixed(1) + "%</span>" +
               judgment(showing) +
               (showing.maxCombo ? '<span class="hs-combo">' +
                                   money(showing.maxCombo) + " combo</span>" : "") +
               "</span>";
        return out + "</div>";
    }

    function showResults(d) {
        var sel = d && d.selectedSong;
        var res = d && d.results && d.results[0];
        if (!sel || !sel.folder) return;

        var id = sel.folder;
        song = { id: id, title: sel.title, courses: {} };
        loadedFor = null;
        paint();
        hide(false);
        setOpen(true);

        var me = playerName();
        var mark = null;
        // An autoplay run is never saved, and in multiplayer the payload
        // does not say which side is the local player, so neither gets
        // attributed to anyone.
        if (me && res && !d.autoPlayEnabled && !d.multiplayer) {
            var good = num(res.good), ok = num(res.ok), bad = num(res.bad);
            var total = good + ok + bad;
            mark = {
                diff: sel.difficulty,
                user: me,
                points: num(res.points),
                landed: false,
                improved: false,
                willLand: true,
                previousRow: null,
                run: {
                    rank: 0, user: me, points: num(res.points),
                    accuracy: total ? (good + ok * 0.5) / total * 100 : 0,
                    crown: crownFor(good, ok, bad),
                    good: good, ok: ok, bad: bad,
                    maxCombo: num(res.maxCombo)
                }
            };
        }

        body.innerHTML = '<div class="hs-msg">Loading\u2026</div>';
        fetchResults(id, mark, ++resultRun, 0);
    }

    function fetchResults(id, mark, run, attempt) {
        fetch(API + id + "?limit=5")
            .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
            .then(function (d) {
                if (run !== resultRun) return;      // a newer song took over
                if (!mark) { render(d); return; }

                var board = (d.boards[mark.diff] || {}).rows || [];
                var existing = null;
                board.forEach(function (r) { if (r.user === mark.user) existing = r; });

                // Capture what they held before the new score lands, so the
                // comparison survives the moment the board is overwritten.
                if (attempt === 0 && existing && existing.points !== mark.points) {
                    mark.previousRow = existing;
                    // taiko-web keeps the better score, so a lesser run is
                    // never going to appear -- don't keep waiting for it.
                    mark.willLand = mark.points > existing.points;
                }
                mark.landed = !!(existing && existing.points === mark.points);
                mark.improved = mark.landed && !!mark.previousRow &&
                                mark.points > mark.previousRow.points;
                render(d, mark);

                if (!mark.landed && mark.willLand &&
                    attempt + 1 < RESULT_RETRIES.length) {
                    setTimeout(function () {
                        if (run === resultRun) fetchResults(id, mark, run, attempt + 1);
                    }, RESULT_RETRIES[attempt + 1] - RESULT_RETRIES[attempt]);
                }
            })
            .catch(function () {
                if (run !== resultRun) return;
                if (mark) {
                    // API unreachable: show the run on its own
                    render({ boards: runOnly(mark) }, mark);
                } else {
                    body.innerHTML =
                        '<div class="hs-msg">No scores for this song yet.</div>';
                }
                if (attempt + 1 < RESULT_RETRIES.length) {
                    setTimeout(function () {
                        if (run === resultRun) fetchResults(id, mark, run, attempt + 1);
                    }, RESULT_RETRIES[attempt + 1] - RESULT_RETRIES[attempt]);
                }
            });
    }

    function runOnly(mark) {
        var boards = {};
        boards[mark.diff] = {
            label: DIFF_LABEL[mark.diff] || mark.diff,
            color: DIFF_COLOR[mark.diff] || "#888",
            stars: 0, players: 0, rows: []
        };
        return boards;
    }

    // ------------------------------------------------------------ events

    function setSong(s) {
        // Random, Search, Settings and similar entries carry no courses.
        var next = (s && s.id && s.courses) ? s : null;
        if ((next && next.id) === (song && song.id)) return;
        song = next;
        loadedFor = null;
        paint();
    }

    function hide(v) {
        if (root) root.classList.toggle("hidden", v);
        // the game draws its own controls over gameplay, so this goes too
        if (fsBtn) fsBtn.classList.toggle("hidden", v);
    }

    // pageEvents.send uses a bare dispatchEvent, so these arrive on window.
    function on(n, fn) { window.addEventListener(n, fn); }

    /* Visibility comes from the game's own events, not from the DOM: #game
       is present on the results screen too, identically and as the only
       child of #screen, so polling for it cannot tell a song being played
       from a song that has just ended.

       load-song is the point of no return -- it fires when the loading
       screen appears, once a difficulty has been confirmed -- and
       game-start follows it. song-select-difficulty is NOT that moment: it
       fires from toSelectDifficulty() when the difficulty screen opens,
       which is exactly where the board is worth reading. */
    on("load-song",              function ()  { hide(true); });
    on("game-start",             function ()  { hide(true); });
    on("load-song-cancel",       function ()  { hide(false); });
    on("load-song-error",        function ()  { hide(false); });

    on("title-screen",           function ()  { setSong(null); hide(false); });
    on("song-select",            function ()  { setSong(null); hide(false); });
    on("song-select-move",       function (e) { setSong(e.detail); hide(false); });
    on("song-select-back",       function ()  { setSong(null); hide(false); });
    on("song-select-difficulty", function (e) { setSong(e.detail); hide(false); });
    on("scoresheet",             function (e) { showResults(e.detail); });

    ["settings", "plugins", "about", "custom-songs", "tutorial", "debug"]
        .forEach(function (n) { on(n, function () { hide(true); }); });

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", build);
    } else {
        build();
    }
})();
