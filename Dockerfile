# The application image: server, client and nginx in one image, run as
# separate containers with different commands (see docker-compose.yml).
#
# This builds from the working tree. It used to be built out-of-tree by
# mia-taiko-web, which cloned this repo and applied its changes as sed
# patches at build time; those changes are now source in this repo.
#
# It ships upstream's assets, which are placeholders for a good part of
# the set. A private overlay image adds the real ones — nothing
# asset-related belongs in this repo.
FROM docker.io/library/python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg nginx \
    && rm -rf /var/lib/apt/lists/*

# Debian ships a default site on port 80 that would shadow our config.
RUN rm -f /etc/nginx/sites-enabled/default \
    && sed -i '/sites-enabled/d' /etc/nginx/nginx.conf

WORKDIR /srv/taiko-web

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf

# assets.js requires 33 images upstream references but does not ship. The
# loader treats a 404 on any of them as fatal, so without this a clean
# checkout stalls at 45% and never reaches the title screen. The overlay
# image copies real artwork over these afterwards.
RUN python3 tools/make-placeholders.py

# version.json is the client's asset cache key and is generated from git,
# which is not in the build context. build.sh writes it before building;
# this fallback keeps a bare `podman build .` working for local use.
RUN [ -f version.json ] \
    || echo '{"commit": "unknown", "commit_short": "dev", "version": "0.0.0"}' > version.json \
    && cat version.json

EXPOSE 34801 34802

CMD ["gunicorn", "-b", "0.0.0.0:34801", "app:app"]
