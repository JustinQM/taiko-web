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

TAIKO_URL = os.environ.get("TAIKO_URL", "http://localhost:34900")

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
        page.on("pageerror", lambda e: self.errors.append(str(e)))

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
        """Every visible setting as {name, value}, in screen order."""
        return self.page.eval_on_selector_all(
            ROWS,
            """els => els.map(el => ({
                name: (el.querySelector('.setting-name') || {}).textContent || '',
                value: (el.querySelector('.setting-value') || {}).textContent || '',
            }))""",
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


@pytest.fixture
def game(page):
    return Game(page).load()
