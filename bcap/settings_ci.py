"""
Lightweight settings layer: the real project settings minus infrastructure that
isn't present in CI / test environments (Redis, a writable log directory). Env
values come from .github/github_env; only what env can't express lives here.
Shared by GitHub Actions management commands and by the test settings.
"""

from bcap.settings import *

# No Redis here. Keep the cache in-process so management commands that load
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

# No writable log directory on a fresh checkout; drop the file handler so
# django.setup() doesn't fail opening it. Console logging stays.
LOGGING["handlers"].pop("file", None)
for _logger in LOGGING["loggers"].values():
    _logger["handlers"] = [h for h in _logger.get("handlers", []) if h != "file"]
