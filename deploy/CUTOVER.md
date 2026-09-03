# Cutting mia over to the fork build

mia is still running the pre-fork image: `taiko-web:latest`, built by
mia-taiko-web cloning this repo and patching it with sed. The new build
is `taiko-web-mia:latest`, built from this repo plus a private asset
layer. This is what changes and in what order.

Written 2026-09-02, before the first cutover, and re-checked against mia
the same day: still on `taiko-web:latest`, `PLUGINS` still in config,
`MULTIPLAYER_BIND` still absent, nginx.conf still bind-mounted. If mia
has been redeployed since, re-check the current state section first.

## The short version

Three things have to land **in the same deploy**:

1. the new image
2. `/mnt/Data/taiko/config.py` gaining `MULTIPLAYER_BIND` and losing
   `PLUGINS`
3. the compose file losing the `nginx.conf` bind mount

Any one of them alone leaves the site broken in a way the other two
would have fixed. See "what breaks out of order".

## Current state on mia

Checked 2026-09-02:

- `taiko-web-nginx-1`, `taiko-web-app-1`, `taiko-web-multiplayer-1` all
  run `taiko-web:latest`; `taiko-web-highscores-1` runs
  `taiko-highscores:latest`
- `/mnt/Data/taiko/config.py` sets `PLUGINS` to three plugin URLs, and
  already sets `SESSION_COOKIE_SECURE = False` and
  `WTF_CSRF_SSL_STRICT = False`
- nginx bind-mounts `/mnt/Data/taiko/nginx.conf` over
  `/etc/nginx/conf.d/default.conf`
- app and nginx bind-mount `/mnt/Data/taiko/songs`; app also mounts
  `config.py`
- the `taiko-web_taiko_public` volume still exists but **no running
  container mounts it**. It is a leftover from when `public/` was a
  named volume. Do not re-add it; the new image bakes `public/` in.
- the stack is a Portainer stack, edited in the Portainer UI, not from a
  compose file on disk

## What changes on mia's side

### config.py

Two edits. Take the current file, do not start from the example, because
it holds the real `SECRET_KEY`.

**Remove** the whole `PLUGINS = [...]` block. The app no longer reads the
option, and the three files it names are no longer in the image.

**Add**:

    MULTIPLAYER_BIND = '0.0.0.0'

`SESSION_COOKIE_SECURE = False` and `WTF_CSRF_SSL_STRICT = False` are
already there and should stay. They were dead options before this build
-- the cookie flag was forced by a sed patch and nothing read the CSRF
one -- and are now the real source of both settings.

Optionally update `URL`, which still points at
`269Seahorse/Better-taiko-web`. Cosmetic; it is the link in the About
screen.

### compose (in Portainer)

The stack is **taiko-web**, under Stacks in the Portainer UI. Editing it
there is the only way to change it: there is no compose file on disk to
edit, and `docker compose` on mia will not find the stack.

- change the three `image:` lines from `taiko-web:latest` to
  `taiko-web-mia:latest`
- delete the nginx `nginx.conf` bind mount line:

      - /mnt/Data/taiko/nginx.conf:/etc/nginx/conf.d/default.conf:ro

  It ships in the image now, at `deploy/nginx.conf`. The deployed copy
  and the image copy are byte-identical apart from comments, so this is
  a no-op at cutover -- but leaving the mount means future changes to the
  config in this repo silently do nothing on mia.

Everything else stays: the songs and config bind mounts, the mongo and
redis paths, the published port 34800.

`mia-taiko-web/docker-compose.yml` already has both changes. The
Portainer stack is a separate copy, so paste the new one in.

## Order

The image can be loaded whenever -- loading it changes nothing until the
stack is redeployed.

    # on the build machine
    cd mia-taiko-web
    ./build.sh                 # builds taiko-web, then the asset layer
    ./deploy.sh <tag>          # streams taiko-web-mia + taiko-highscores

Then, in one sitting:

1. edit `/mnt/Data/taiko/config.py` (both edits)
2. update the Portainer stack (image names, drop the nginx mount)
3. redeploy the stack

In Portainer, step 3 is **Stacks -> taiko-web -> Update the stack**, with
**Re-pull image** left OFF. The images are local -- loaded by deploy.sh,
not pulled from a registry -- and asking Portainer to re-pull them makes
it try a registry that does not have them and fail the deploy. `Prune
services` off as well; nothing has been removed from the stack.

Portainer restarts every container in the stack, including mongo and
redis. That is fine -- both have their data on bind mounts under
`/mnt/Data/taiko` -- but the site is down for the few seconds it takes.

Config first, because the app reads it at startup and step 3 is what
restarts it. Doing it the other way means the app comes up on the old
config and needs a second restart.

## What breaks out of order

| you do | you get |
| --- | --- |
| new image, `PLUGINS` left in config | the client requests three `/src/plugins/*.js` that are not in the image. They 404. Not fatal -- the loader logs and continues -- but the scroll speed, spartan and skip-results settings are already built in, so leaving them achieves nothing and makes the console noisy. |
| new image, no `MULTIPLAYER_BIND` | **`/p2` returns 502 and multiplayer is dead.** The bind address is a config option now and defaults to `localhost`, which nginx cannot reach from its own container. The old image had `0.0.0.0` forced in by a sed patch, so this is the one that bites hardest. |
| config updated, old image still running | `MULTIPLAYER_BIND` is ignored (the old image does not read it) and removing `PLUGINS` disables the three plugins. Site works, minus scroll speed and skip-results, until the new image lands. Harmless and reversible. |
| new image, nginx mount left in place | works, because the two configs are identical today. It will quietly stop tracking this repo, so a later nginx change appears to do nothing. |
| re-adding the `taiko_public` volume | `public/` gets shadowed by the stale volume contents and asset changes stop taking effect. This is what the old README's "remove the volume after every image update" dance was about. Do not. |

## Checks after redeploying

    curl -s -o /dev/null -w '%{http_code}\n' http://mia:34800/            # 200
    curl -s -o /dev/null -w '%{http_code}\n' http://mia:34800/p2          # 426, not 502
    curl -s http://mia:34800/api/songs | jq length                        # ~3367
    curl -s -o /dev/null -w '%{http_code}\n' http://mia:34800/highscores/ # 200
    curl -s http://mia:34800/api/config | jq '.plugins, ._version'        # null, new tag

426 on `/p2` is correct: it is a websocket endpoint answering a plain
HTTP request. 502 means `MULTIPLAYER_BIND` did not take.

In a browser: the title screen should reach "Click or Press Enter!" with
nothing 404ing in the network tab, and the settings screen should list
Song Select Speed and the three Spartan Mode rows.

Log in and out once. The session cookie is issued fresh and the old
session predates the config change.

## Rollback

**The pre-fork image is gone.** It was cleaned up on 2026-09-02, after
the cutover had been running all day, along with every base image and
every superseded build. What is left on mia is the current
`taiko-web-mia:latest` and one build behind it under its date tag --
`docker images taiko-web-mia` shows what there is.

So rollback now means the previous fork build, not the pre-fork one:
set the three `image:` lines to that date tag and redeploy. Config and
compose stay as they are; every fork build wants the same ones.

Going back to the pre-fork build would mean rebuilding it from the
upstream revision and putting `PLUGINS` back in `config.py`. Nothing has
needed that, and the further the two diverge the less likely it is to be
the right answer -- the scores and songs are shared either way.

Nothing in this change touches mongo, redis or the songs directory, so
there is no data to roll back and no migration to undo. Scores, users and
songs are untouched.

The one thing that does not roll back automatically: browsers that loaded
the new build cached its assets under a new cache key --
`?<commit>-<tag>-<source hash>-<asset hash>`. Rolling back serves the old
key again, so they will re-fetch. No action needed, just expect a slow
first load.

## Not part of this cutover

- `tools/highscores` moved into this repo and is built by `build.sh`, but
  it is the same service and the same image name, so the highscores
  container needs nothing beyond the redeploy.
- Songs and the import pipeline are unchanged and still run from
  mia-taiko-web.
