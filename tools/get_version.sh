#!/usr/bin/env bash
# Writes version.json. The client uses commit_short as its asset cache
# key: every script, stylesheet and asset URL is emitted as ...?<key>,
# and nginx serves those immutable for a year.
#
# So the key has to follow the *content*, not the commit. It used to be
# the commit plus BUILD_TAG, and BUILD_TAG is the image tag, which for a
# local build is the constant "local" -- so rebuilding a changed working
# tree shipped new files under a URL the browser already had cached, and
# it would never ask for them again. A fix you cannot see is worse than
# no fix; the whole point of immutable caching is that it believes you.
#
# The hash covers everything the client loads out of this repo. Private
# assets are layered on top by another image and change under names that
# stay the same, so that build folds its own hash in as well.
set -euo pipefail

toplevel=$( git rev-parse --show-toplevel )

# Tracked and untracked, ignored files excluded: the same set the image
# is built from.
content=$(
    cd "$toplevel" && git ls-files -z --cached --others --exclude-standard \
        -- public/src public/assets templates \
    | sort -z | xargs -0 -r sha1sum | sha1sum | cut -c1-8
)

git -C "$toplevel" log -1 \
    --pretty="format:{\"commit\": \"%H\", \"commit_short\": \"%h${BUILD_TAG:+-$BUILD_TAG}-$content\", \"version\": \"%ad\"}" \
    --date="format:%y.%m.%d" > "$toplevel/version.json"
