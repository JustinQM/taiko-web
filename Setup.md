# Setup

Docker. The old bare-metal instructions are gone — this fork builds and
runs as a container stack.

You need Docker with Compose, and songs. taiko-web reads TJA and osu
charts. **This repository ships no game assets, songs, audio, images,
fonts or chart media.** You provide your own.

## Running it

```sh
git clone https://github.com/JustinQM/taiko-web
cd taiko-web
cp config.example.py config.py
docker compose up -d
```

That brings up six containers — mongo, redis, the app, the multiplayer
server, nginx and the leaderboard — and serves on port 34800.

Edit `config.py` before starting if you need to. `SECRET_KEY` should be
something real: `openssl rand -hex 32`. `SESSION_COOKIE_SECURE` must be
`False` if you're serving over plain HTTP, or browsers drop the session
cookie and nobody can log in.

## First run

Import the song genres:

```sh
docker compose exec -T mongo mongoimport --db taiko \
  --collection categories --jsonArray < tools/categories.json
```

Register an account in the browser, then make it an admin:

```sh
docker compose exec -T mongo mongosh taiko --eval \
  'db.users.findOneAndUpdate({username:"yourname"},{$set:{user_level:100}})'
```

Log out and back in — the session caches the old level.

## Adding songs

Each song is a numbered directory under `public/songs/` matching its
database id, containing `main.tja` and `main.ogg`. Ogg is fine for the
audio; only previews need MP3, and the app generates those itself.

Add the metadata at `/admin/songs` once you're logged in as an admin.

For a library of any size, script it. The song document needs `id`,
`title`, `courses` with stars per difficulty, `category_id`, `music_type`
and a `hash` — the md5 of `main.tja`, which is what scores are keyed on.
Without the hash, scores can't be saved.

## Assets

The game references images it doesn't ship. Blank placeholders are
generated at build so it boots, but it'll look wrong.

Layer your own over the built image:

```dockerfile
FROM taiko-web:latest
COPY assets/img/ /srv/taiko-web/public/assets/img/
COPY assets/audio/ /srv/taiko-web/public/assets/audio/
```

Or host them elsewhere and point `ASSETS_BASEURL` at it.

## Updating

```sh
git pull
docker compose build
docker compose up -d
```

Client assets are cached by a key derived from the build, so browsers
pick up changes without anyone clearing anything.

## Development

```sh
docker compose -f docker-compose.dev.yml up -d   # :34910
pytest tests/
```

The Playwright suite runs against that stack.
