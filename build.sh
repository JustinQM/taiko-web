#!/usr/bin/env bash
# Build the application and leaderboard images.
#
# This repo used to be built out-of-tree: mia-taiko-web cloned it and
# applied its changes as sed patches, so build.sh took an upstream
# revision. Everything is source here now, so it builds the working tree
# and there is nothing to pin.
set -euo pipefail

cd "$(dirname "$0")"

IMAGE="${IMAGE:-taiko-web}"
HS_IMAGE="${HS_IMAGE:-taiko-highscores}"
TAG="${TAG:-$(date +%Y%m%d-%H%M)}"
ENGINE="${ENGINE:-podman}"

info() { printf '\033[36m::\033[0m %s\n' "$*"; }

# This repo is public and must never carry game assets; see the script.
info "checking for asset material"
tools/check-no-assets.sh

# version.json is the client's asset cache key. It has to differ between
# builds or browsers keep serving stale JS out of the HTTP cache and
# IndexedDB; BUILD_TAG makes it do so even when the commit has not moved.
info "writing version.json (build tag $TAG)"
BUILD_TAG="$TAG" tools/get_version.sh
cat version.json
echo

info "building $IMAGE:$TAG"
"$ENGINE" build -t "$IMAGE:$TAG" -t "$IMAGE:latest" .

# Built from the repository root, not highscores/, because its font subset
# is generated from public/assets/fonts/TnT.ttf.
info "building $HS_IMAGE:$TAG"
"$ENGINE" build -f highscores/Dockerfile -t "$HS_IMAGE:$TAG" -t "$HS_IMAGE:latest" .

echo
info "built $IMAGE:$TAG and $HS_IMAGE:$TAG"
info "deploy with:  ./deploy.sh $TAG"
