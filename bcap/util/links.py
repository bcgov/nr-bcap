from django.conf import settings


def app_url(path):
    """Absolute URL to an app path. PUBLIC_SERVER_ADDRESS is the full hosted base
    including any sub-path mount (eg http://localhost:82/bcap/), so the path is
    appended to it directly."""
    return settings.PUBLIC_SERVER_ADDRESS.rstrip("/") + "/" + path.lstrip("/")
