#!/usr/bin/env bash
# Seed the local test stack (docker-compose.dev.yml) from production.
#
# Read-only against the remote host: it runs mongodump inside the running
# mongo container and streams the archive over ssh. Nothing is written
# there and nothing is restarted there.
#
# The local stack has no song audio and no real assets, so nothing is
# playable afterwards -- this is about having real songs, scores and users
# for the song wheel and the leaderboard to render.
set -euo pipefail

MIA="${MIA:-mia}"
MONGO_PORT="${MONGO_PORT:-27117}"
NGINX_PORT="${NGINX_PORT:-34900}"
STACK="${STACK:-taiko-web}"
ARCHIVE="${ARCHIVE:-$(mktemp -t taiko-XXXXXX.archive)}"

info() { printf '\033[36m::\033[0m %s\n' "$*"; }

info "dumping taiko from $MIA"
ssh "$MIA" 'docker exec $(docker ps -qf name=taiko.*mongo) mongodump --db taiko --archive' > "$ARCHIVE"
info "archive is $(du -h "$ARCHIVE" | cut -f1)"

info "restoring into localhost:$MONGO_PORT"
mongorestore --uri "mongodb://127.0.0.1:$MONGO_PORT" --archive="$ARCHIVE" --drop

# The app caches the song list at startup and the leaderboard only polls
# mongo once a minute, so both have to be restarted to see the new data.
# Restarting them changes their container addresses, and nginx resolves
# its upstreams only at startup -- so nginx has to follow or every request
# 502s afterwards.
info "restarting app and highscores, then nginx (which caches their addresses)"
docker restart "${STACK}-app-1" >/dev/null
docker restart "${STACK}-highscores-1" >/dev/null
docker restart "${STACK}-nginx-1" >/dev/null
sleep 5

count=$(curl -s "http://localhost:$NGINX_PORT/api/songs" \
        | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
info "done -- $count songs live on http://localhost:$NGINX_PORT"
