#!/usr/bin/env bash
# Writes version.json. The client uses commit_short as its asset cache key:
# every script and asset URL is emitted as ...?<commit_short>.
#
# BUILD_TAG is appended when set. Without it the cache key only changes
# when the commit does, so a rebuild that changed assets, config or the
# private overlay keeps the same query string, and browsers keep serving
# stale JS out of both the HTTP cache and IndexedDB. build.sh sets it to
# the image tag so every deploy invalidates cleanly.
toplevel=$( git rev-parse --show-toplevel )
git log -1 --pretty="format:{\"commit\": \"%H\", \"commit_short\": \"%h${BUILD_TAG:+-$BUILD_TAG}\", \"version\": \"%ad\"}" --date="format:%y.%m.%d" > "$toplevel/version.json"
