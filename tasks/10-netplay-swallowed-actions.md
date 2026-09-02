# 10 — The netplay branch that swallows actions

`toSelectDifficulty`'s session branch sends a selection for anything with
courses and does nothing at all for anything else. Search and Random were
fixed by naming them explicitly; every other action still falls into that
branch and disappears without a sound, a message or any sign it was
pressed.

That is now folder, back, settings, about, how to play — some of which
should work in a session and some of which should say they cannot.

## What it changes

Make the branch total: every action is either handled, sent, or
explicitly refused with the cancel sound, and nothing falls through
silently.

## How it will be shown to work

Drive every entry type through `toSelectDifficulty` in a stubbed session
and assert each one does something. The existing dispatch tests cover
four of them; this extends to all of them and adds a check that no action
is unhandled.
