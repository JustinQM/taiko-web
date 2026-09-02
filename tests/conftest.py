"""Browser-test fixtures for the game client.

public/src/js is canvas and DOM with no build step and no module system,
so there is no way to exercise it except in a browser. These tests drive
a real one against a running stack.

    docker compose -f docker-compose.dev.yml up -d
    pytest tests/

Point them somewhere else with TAIKO_URL. They are read-only apart from
localStorage, so running them against a live deployment is safe, but the
default is the local stack.
"""

import os

import pytest

TAIKO_URL = os.environ.get("TAIKO_URL", "http://localhost:34910")

# The public stack ships no songs, so every preview and chart request
# fails there by design. Those are not the errors these tests are looking
# for.
IGNORED_ERRORS = ("/songs/",)

# The settings screen's own list. The gamepad and latency sub-windows are
# nested .view-content elements inside it, so an unscoped .setting-box
# picks up their rows too.
ROWS = ".settings-outer > .view > .view-content > .setting-box"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # The settings screen starts its background music in init(); without
    # this Chromium blocks it as autoplay and the screen never finishes
    # loading.
    return {
        **browser_type_launch_args,
        "args": ["--autoplay-policy=no-user-gesture-required"],
    }


class Game:
    """Thin driver for the parts of the client these tests touch."""

    def __init__(self, page):
        self.page = page
        self.errors = []
        page.on("pageerror", lambda e: self._record(str(e)))

    def _record(self, message):
        if not any(ignore in message for ignore in IGNORED_ERRORS):
            self.errors.append(message)

    def load(self):
        self.page.goto(TAIKO_URL, wait_until="networkidle", timeout=60000)
        # The loader pulls in every script before these exist.
        self.page.wait_for_function(
            "() => typeof SettingsView !== 'undefined' && typeof settings !== 'undefined'",
            timeout=30000,
        )
        return self

    def open_settings(self):
        """Open the settings screen directly.

        Going through the title screen and song select would make every
        test depend on song select navigation, which is being reworked.
        SettingsView is the unit under test either way -- song select just
        calls this constructor.
        """
        self.page.evaluate("() => new SettingsView(false)")
        self.page.wait_for_selector(ROWS, timeout=15000)
        return self

    def rows(self):
        """Every visible setting as {name, value}, in screen order.

        Number settings put their -/+ adjust buttons inside .setting-value,
        so the buttons are stripped before reading the text; otherwise the
        speed row reads as "2x-+".
        """
        return self.page.eval_on_selector_all(
            ROWS,
            """els => els.map(el => {
                const nameEl = el.querySelector('.setting-name')
                const valueEl = el.querySelector('.setting-value')
                let value = ''
                if(valueEl){
                    const clone = valueEl.cloneNode(true)
                    clone.querySelectorAll('.latency-buttons').forEach(b => b.remove())
                    value = clone.textContent
                }
                return {name: nameEl ? nameEl.textContent : '', value: value}
            })""",
        )

    def row(self, name):
        for row in self.rows():
            if row["name"].strip() == name:
                return row
        raise AssertionError(
            f"no setting row named {name!r}; found "
            f"{[r['name'].strip() for r in self.rows()]}"
        )

    def click(self, name):
        """Activate a row by its visible name, as a mouse user would."""
        self.page.click(f"{ROWS}:has(.setting-name:text-is('{name}'))")
        return self

    def stored(self, key):
        """What was actually written to localStorage, not what is drawn."""
        return self.page.evaluate(
            "key => JSON.parse(localStorage.getItem('settings') || '{}')[key]", key
        )

    def setting(self, key):
        """The value the client resolves for a key, defaults included."""
        return self.page.evaluate("key => settings.getItem(key)", key)

    # ------------------------------------------------------------ song select

    def open_song_select(self):
        """Construct SongSelect directly, as the title screen would.

        The tutorial flag is set first: without it a fresh profile is sent
        to the tutorial instead.
        """
        self.page.wait_for_function(
            "() => typeof SongSelect !== 'undefined' && assets.songs.length",
            timeout=40000,
        )
        self.page.evaluate("""() => {
            try { localStorage.setItem("tutorial", "true") } catch(e) {}
            window.__ss = new SongSelect(false, false, false)
        }""")
        return self

    def settle(self, timeout=5000):
        """Wait for a move animation to finish.

        state.locked is 1 while the wheel is sliding and drops back to 0
        when redraw has applied the move.
        """
        self.page.wait_for_function("() => __ss.state.locked === 0", timeout=timeout)
        return self

    def wheel(self):
        return self.page.evaluate("""() => ({
            total: __ss.songs.length,
            selected: __ss.selectedSong,
            screen: __ss.state.screen,
            title: __ss.songs[__ss.selectedSong].title,
            category: __ss.songs[__ss.selectedSong].category,
            action: __ss.songs[__ss.selectedSong].action || null,
        })""")

    def move(self, by):
        self.page.evaluate("by => __ss.moveToSong(by)", by)
        return self.settle()

    def category_jump(self, by):
        self.page.evaluate("by => __ss.categoryJump(by)", by)
        return self.settle()

    def select_index(self, index):
        """Put the cursor on a given entry without animating there."""
        self.page.evaluate("i => { __ss.selectedSong = i; __ss.state.move = 0 }", index)
        return self

    def enter_folder(self, index=0):
        """Descend into a folder, leaving the cursor on its first song."""
        self.select_index(index)
        self.page.evaluate("() => __ss.toFolder()")
        self.page.wait_for_function("() => __ss.navigator.path.length > 0", timeout=5000)
        return self

    def leave_folder(self):
        self.page.evaluate("() => __ss.toFolderUp()")
        self.page.wait_for_function("() => __ss.navigator.path.length === 0", timeout=5000)
        return self

    def path(self):
        return self.page.evaluate("() => __ss.navigator.path.map(f => f.id)")

    def enter_folder(self, index=0):
        """Descend into a folder, leaving the cursor on its first song."""
        self.select_index(index)
        self.page.evaluate("() => __ss.toFolder()")
        self.page.wait_for_function("() => __ss.navigator.path.length > 0", timeout=5000)
        return self

    def leave_folder(self):
        self.page.evaluate("() => __ss.toFolderUp()")
        self.page.wait_for_function("() => __ss.navigator.path.length === 0", timeout=5000)
        return self

    def path(self):
        return self.page.evaluate("() => __ss.navigator.path.map(f => f.id)")


@pytest.fixture
def game(page):
    return Game(page).load()
