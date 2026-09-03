# 19 — A rebuild has to change the cache key

Do this one first: two of the five things reported are already fixed and
cannot be seen.

The performance pass made everything under `/assets/` and `/src/`
immutable for a year and gave every URL a query string so a deploy
invalidates them. The query string is `<commit_short>-<image tag>`, and
for a local build the image tag is always `local`. So a rebuild from a
working tree that has changed but not been committed ships new files
under the **old** URL, and a browser that has seen the old ones will
never ask again. That is what immutable means.

Which is why the results screen still has no Don-chan and the
background still has black bars down the sides: both were fixed, both
shipped under `?efb41c4-local`, and the browser had already cached
`?efb41c4-local`.

## What it changes

`tools/get_version.sh` hashes what actually ships -- the client source,
the templates and the assets -- into the key, so the key follows the
content rather than the commit. The private overlay does the same with
the real assets it adds on top, since those change under names that
stay the same.

## How it will be shown to work

Build twice from the same commit with one file changed between, and the
two keys differ. Build twice with nothing changed and they match.
