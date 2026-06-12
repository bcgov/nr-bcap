"""
CI settings: the real project settings with the few overrides GitHub Actions
needs. Env values come from .github/github_env; only what env can't express
lives here.
"""

from bcap.settings import *

# CI has no Redis. Keep the cache in-process so management commands that load
# settings (check, makemigrations) don't reach for a broker that isn't there.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    },
    "user_permission": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "user_permission_cache",
    },
}
