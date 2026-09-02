# Config for the local test stack (docker-compose.dev.yml). Committed on
# purpose: it holds no secret, and the stack is bound to localhost only.
# Real deployments copy config.example.py instead.
ASSETS_BASEURL = '/assets/'
SONGS_BASEURL = '/songs/'
EMAIL = None
ACCOUNTS = True
CUSTOM_JS = '/src/custom.js'
PLUGINS = []
PREVIEW_TYPE = 'mp3'

# nginx runs in a separate container and cannot reach localhost here.
MULTIPLAYER_BIND = '0.0.0.0'

MONGO = {
    'host': ['mongo:27017'],
    'database': 'taiko'
}

REDIS = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_HOST': 'redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_PASSWORD': None,
    'CACHE_REDIS_DB': None
}

SECRET_KEY = 'local-development-only'

# The stack is plain HTTP on localhost, mirroring the production
# deployment. Without these the browser drops the session cookie and
# registration fails with "Security token expired".
SESSION_COOKIE_SECURE = False
WTF_CSRF_SSL_STRICT = False
URL = 'https://github.com/JustinQM/taiko-web/'

GOOGLE_CREDENTIALS = {
    'gdrive_enabled': False,
    'api_key': '',
    'oauth_client_id': '',
    'project_number': '',
    'min_level': None
}
