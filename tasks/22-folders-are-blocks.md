# 22 — Folders are blocks, songs are slats

A folder and a song look the same in the wheel: an 82px slat with the
name written down it, differing only in colour. There is no way to tell
at a glance where the folders are.

Making folders always draw at their opened width fixes that. Worth
saying plainly: YataiDON does not do this -- its folders are the same
width as its songs and are told apart by the genre art and name on the
closed box. But the problem is real and this does solve it.

## What it changes

The wheel currently places boxes by index: every one is 82 wide plus an
18px margin, so a position is a multiplication. With folders at 382 that
stops being true, so the layout is walked and accumulated instead, and
the same walk feeds the mouse hit-testing, which does the same
multiplication today.

## How it will be shown to work

A screenshot of a wheel with folders in it, and a test that clicking a
box selects the box that was clicked when a folder sits between.
