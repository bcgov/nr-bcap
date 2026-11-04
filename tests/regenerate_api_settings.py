"""Settings for the regenerate_api --check CI step.

regenerate_api (arches_zod_validation) has no --target flag like
regen_python_aliases does, so it can't switch to the test database on its own.
Point the default database at test_bcap, which already has the full Arches
schema from the manage.py test --keepdb step that always precedes this check.
"""

from tests.test_settings import *  # noqa: F401, F403

DATABASES = {
    **DATABASES,
    "default": {
        **DATABASES["default"],
        "NAME": "test_bcap",
    },
}
