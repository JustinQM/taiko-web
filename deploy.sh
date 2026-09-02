#!/usr/bin/env bash
# Stream the built images to a remote docker host over ssh.
#
# No registry and no credentials: the local engine writes an image archive
# to stdout, piped into docker load on the far side. The tradeoff is that
# rolling back to an older tag means rebuilding it, unless that tag is
# still in the remote image store.
set -euo pipefail

TAG="${1:-latest}"
IMAGE="${IMAGE:-taiko-web}"
HS_IMAGE="${HS_IMAGE:-taiko-highscores}"
HOST="${HOST:-${MIA:-mia}}"
ENGINE="${ENGINE:-docker}"

info() { printf '\033[36m::\033[0m %s\n' "$*"; }

for image in "$IMAGE" "$HS_IMAGE"; do
    info "streaming $image:$TAG to $HOST"
    "$ENGINE" save "$image:$TAG" | ssh "$HOST" 'docker load'

    # podman save labels images localhost/<name>, docker does not. Retag
    # to the bare name the compose file expects if the prefixed one turned
    # up, then move :latest either way.
    info "retagging $image:$TAG"
    ssh "$HOST" "
        if docker image inspect localhost/$image:$TAG >/dev/null 2>&1; then
            docker tag localhost/$image:$TAG $image:$TAG
            docker rmi localhost/$image:$TAG >/dev/null
        fi
        docker tag $image:$TAG $image:latest"
done

echo
ssh "$HOST" "docker images | grep -E '^($IMAGE|$HS_IMAGE) '"
echo
info "images are loaded; redeploy the stack to pick them up"
