# The full URL base asset URL, with trailing slash.
ASSETS_BASEURL = '/assets/'

# The full URL base song URL, with trailing slash.
SONGS_BASEURL = '/songs/'

# The email address to display in the "About Simulator" menu.
EMAIL = None

# Whether to use the user account system.
ACCOUNTS = True

# Custom JavaScript file to load with the simulator.
CUSTOM_JS = ''

# Default plugins to load with the simulator.
PLUGINS = [{
    'url': '',
    'start': False,
    'hide': False
}]

# Address the multiplayer server binds to. Use '0.0.0.0' when it runs in
# its own container, so the reverse proxy can reach it; the default is
# only reachable from the same host.
MULTIPLAYER_BIND = 'localhost'

# Filetype to use for song previews. (mp3/ogg)
PREVIEW_TYPE = 'mp3'

# MongoDB server settings.
MONGO = {
    'host': ['127.0.0.1:27017'],
    'database': 'taiko'
}

# Redis server settings, used for sessions + cache.
REDIS = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': '127.0.0.1',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_PASSWORD': None,
    'CACHE_REDIS_DB': None
}

# Secret key used for sessions.
SECRET_KEY = 'change-me'

# Set both to False when serving over plain HTTP, e.g. on a private
# network behind a reverse proxy that does not terminate TLS. Leaving them
# True over HTTP makes the browser drop the session cookie, and
# registration then fails with "Security token expired".
SESSION_COOKIE_SECURE = True
WTF_CSRF_SSL_STRICT = True

# Git repository base URL.
URL = 'https://github.com/bui/taiko-web/'

# Google Drive API.
GOOGLE_CREDENTIALS = {
    'gdrive_enabled': False,
    'api_key': '',
    'oauth_client_id': '',
    'project_number': '',
    'min_level': None
}
