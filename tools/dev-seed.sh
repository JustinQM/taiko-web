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
ARCHIVE="${ARCHIVE:-$(mktemp -t taiko-XXXXXX.archive)}"

info() { printf '\033[36m::\033[0m %s\n' "$*"; }

info "dumping taiko from $MIA"
ssh "$MIA" 'docker exec $(docker ps -qf name=taiko.*mongo) mongodump --db taiko --archive' > "$ARCHIVE"
info "archive is $(du -h "$ARCHIVE" | cut -f1)"

info "restoring into localhost:$MONGO_PORT"
mongorestore --uri "mongodb://127.0.0.1:$MONGO_PORT" --archive="$ARCHIVE" --drop

# The app caches the song list at startup, so it has to be restarted to see
# the new data. Restarting it gives it a new container IP, and nginx only
# resolves its upstreams at startup -- so nginx has to follow or every
# request 502s.
info "restarting app, then nginx (which caches the app's address)"
podman restart taiko-web_app_1 >/dev/null
podman restart taiko-web_nginx_1 >/dev/null
sleep 4

count=$(curl -s "http://localhost:$NGINX_PORT/api/songs" \
        | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))')
info "done -- $count songs live on http://localhost:$NGINX_PORT"
