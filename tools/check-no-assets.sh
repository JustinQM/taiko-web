#!/usr/bin/env bash
# Fail if game asset material has entered this repository.
#
# This repo is public. The assets used by the real deployment are ripped
# from a commercial game, and forks that shipped them were taken down in
# 2023. They live in a separate private repo that builds an overlay image
# on top of this one, and nothing asset-related may cross that line.
#
# What this does NOT do: clean up what upstream already ships. public/
# assets/ at the pinned revision below contains real artwork, audio and
# two commercial fonts, all inherited from upstream and present in history
# that predates this fork. That exposure cannot be undone here. This check
# exists to stop *new* material being added.
#
# Run by build.sh. Run it by hand before pushing.
set -uo pipefail

# The upstream commit public/assets/ is pinned to. Bump this only when
# deliberately merging upstream, and check what the merge brought in.
UPSTREAM_REV="${UPSTREAM_REV:-a1c934d46207807bdac9fd99a7f1ce0bb0768f97}"

cd "$(dirname "$0")/.."

fail=0
note() { printf '\033[31m!!\033[0m %s\n' "$*"; fail=1; }
ok()   { printf '\033[32mok\033[0m %s\n' "$*"; }

if ! git rev-parse --verify -q "$UPSTREAM_REV^{commit}" >/dev/null; then
    echo "cannot resolve upstream revision $UPSTREAM_REV" >&2
    exit 2
fi

# 1. public/assets/ must be byte-identical to upstream. Any addition,
#    modification or deletion is a change to shipped asset material.
changed=$(git diff --name-status "$UPSTREAM_REV" -- public/assets)
if [ -n "$changed" ]; then
    note "public/assets/ differs from upstream $UPSTREAM_REV:"
    printf '%s\n' "$changed" | sed 's/^/     /'
else
    ok "public/assets/ matches upstream"
fi

# 2. Untracked files under public/assets/ never reach a commit, but jj
#    snapshots the working copy, so catch them before they do.
untracked=$(git ls-files --others --exclude-standard -- public/assets)
if [ -n "$untracked" ]; then
    note "untracked files under public/assets/:"
    printf '%s\n' "$untracked" | sed 's/^/     /'
else
    ok "no untracked files under public/assets/"
fi

# 3. The plugin drop directory is where the private repo's plugins used to
#    be copied in. Nothing should land there. This looks at the filesystem
#    rather than at git, because the directory is gitignored and so is
#    invisible to `git ls-files --others --exclude-standard`.
plugins=$( { git ls-files -- public/src/plugins
             [ -d public/src/plugins ] && find public/src/plugins -type f; } 2>/dev/null | sort -u)
if [ -n "$plugins" ]; then
    note "public/src/plugins/ is not empty:"
    printf '%s\n' "$plugins" | sed 's/^/     /'
else
    ok "public/src/plugins/ is empty"
fi

# 4. No new binaries anywhere outside public/assets/. git reports a binary
#    diff as '-' in both numstat columns; anything matching an asset
#    extension is caught by name whether or not git calls it binary.
binaries=$(git diff --numstat "$UPSTREAM_REV" \
           | awk -F'\t' '$1 == "-" && $2 == "-" { print $3 }' \
           | grep -v '^public/assets/' || true)
by_name=$(git diff --name-only "$UPSTREAM_REV" \
          | grep -Ei '\.(png|jpe?g|gif|webp|bmp|svg|ico|ogg|mp3|wav|m4a|flac|ttf|otf|woff2?|eot)$' \
          | grep -v '^public/assets/' || true)
offenders=$(printf '%s\n%s\n' "$binaries" "$by_name" | sort -u | sed '/^$/d')
if [ -n "$offenders" ]; then
    note "binary or asset-typed files added outside public/assets/:"
    printf '%s\n' "$offenders" | sed 's/^/     /'
else
    ok "no binaries added outside public/assets/"
fi

if [ "$fail" -ne 0 ]; then
    echo
    echo "asset check FAILED -- do not push" >&2
    exit 1
fi
echo
echo "asset check passed"
