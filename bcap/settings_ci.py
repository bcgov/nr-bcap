"""
CI settings: the unit-test settings plus the one tweak GitHub Actions needs so
CI behaves like a local test run. Env values come from .github/github_env.
"""

from tests.test_settings import *

# CI has no writable log directory on a fresh checkout; drop the file handler
# so django.setup() doesn't fail opening it. Local runs keep it (the dir exists).
LOGGING["handlers"].pop("file", None)
for _logger in LOGGING["loggers"].values():
    _logger["handlers"] = [h for h in _logger.get("handlers", []) if h != "file"]
