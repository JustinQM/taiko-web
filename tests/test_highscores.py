"""The leaderboard's crown counting.

Crowns are cumulative: a chart you full comboed counts as a full combo
and as a clear, and a donderful counts as all three. That is one claim
made in three places which have to agree -- the counts on the standings,
the score behind them, and the two ways of filtering a player's charts
by crown. If they drift apart the site is quietly lying about how much
someone has done, which nothing else would catch.

Plain HTTP rather than a browser: these are server-rendered pages and
there is nothing to drive.
"""

import re
import urllib.request

import pytest

from conftest import TAIKO_URL

BOARD = TAIKO_URL + "/highscores"
KINDS = ["rainbow", "gold", "silver"]


def get(path):
    with urllib.request.urlopen(BOARD + path, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def standings():
    """Every player on the front page: crown counts, score, crowned charts."""
    html = get("/")
    rows = []
    for block in re.findall(
        r'<td class="k-name">(.*?)</td>\s*<td class="k-crowns">(.*?)</td>'
        r'\s*<td class="num k-total">(.*?)</td>', html, re.S):
        name_cell, crown_cell, total_cell = block
        name = re.search(r'/highscores/user/([^"?]+)', name_cell)
        counts = re.findall(r'\?crown=(\w+)[^"]*"[^>]*>.*?([0-9]+)</a>', crown_cell, re.S)
        points = re.search(r'>([0-9]+)</a>', total_cell)
        raw = re.search(r'<em class="raw">([0-9]+) crown', total_cell)
        if not (name and points and raw):
            continue
        rows.append({
            "name": name.group(1),
            "crowns": {k: int(v) for k, v in counts},
            "points": int(points.group(1)),
            "charts": int(raw.group(1)),
        })
    return rows


def charts_shown(name, query):
    """How many chart rows a filtered view of a player actually lists."""
    return len(re.findall(r'<tr data-filter-text',
                          get("/user/" + name + query)))


@pytest.fixture(scope="module")
def players():
    rows = [r for r in standings() if r["points"]]
    if not rows:
        pytest.skip("no crowned players on this stack")
    return rows


def test_the_counts_are_cumulative(players):
    """Every clear count includes the full combos, and those the donderfuls."""
    for p in players:
        c = p["crowns"]
        assert c["silver"] >= c["gold"] >= c["rainbow"], p


def test_the_score_is_the_crowns_added_up(players):
    """No weighting: the number is the three rows summed.

    It comes to what the old 3/2/1 weighting gave, which is the point --
    counting a donderful once per row is what multiplying by three stood
    in for -- but it is now a sum a player can check by looking.
    """
    for p in players:
        assert p["points"] == sum(p["crowns"][k] for k in KINDS), p


def test_the_crowned_chart_count_is_the_clears(players):
    """Every crown is at least a clear, so that row counts the charts."""
    for p in players:
        assert p["charts"] == p["crowns"]["silver"], p


def test_clicking_a_crown_lists_as_many_charts_as_it_claims(players):
    """The counts are links, and they have to land on that many charts.

    This is what makes the cumulative counting safe to show: asking for
    the clears means every chart that is at least cleared.
    """
    p = players[0]
    for kind in KINDS:
        if not p["crowns"][kind]:
            continue
        assert charts_shown(p["name"], "?crown=" + kind) == p["crowns"][kind], kind


def test_any_crown_is_the_same_as_the_clears(players):
    p = players[0]
    assert charts_shown(p["name"], "?crown=any") == p["crowns"]["silver"]


def test_only_this_crown_narrows_to_charts_that_stopped_there(players):
    """The list of what to go back and improve.

    A clear that is not yet a full combo, a full combo not yet donderful.
    Those exclusive groups have to partition the cumulative clears, or one
    of the two filters is wrong.
    """
    p = players[0]
    exact = {k: charts_shown(p["name"], "?crown=%s&crown_mode=only" % k) for k in KINDS}
    assert sum(exact.values()) == p["crowns"]["silver"], exact
    for kind in KINDS:
        assert exact[kind] <= p["crowns"][kind], kind
    # nothing outranks a donderful, so there its two meanings coincide
    assert exact["rainbow"] == p["crowns"]["rainbow"]


def test_only_never_shows_more_than_or_better(players):
    p = players[0]
    for kind in KINDS:
        loose = charts_shown(p["name"], "?crown=" + kind)
        tight = charts_shown(p["name"], "?crown=%s&crown_mode=only" % kind)
        assert tight <= loose, kind


def test_the_toggle_is_offered_once_a_crown_is_picked(players):
    """And not before: "only this" says nothing without a crown to mean."""
    p = players[0]
    assert "crown_mode=only" not in get("/user/" + p["name"])
    assert "crown_mode=only" in get("/user/" + p["name"] + "?crown=silver")
    # "any crown" has no single crown to narrow to either
    assert "crown_mode=only" not in get("/user/" + p["name"] + "?crown=any")
