"""The request resource saves run under."""

from copy import copy

from django.contrib.auth import get_user_model
from django.http import HttpRequest


def acting_request(request=None):
    """The request to save resources under, so every caller takes one path.

    arches-querysets otherwise splits three ways: a real request, force_admin,
    or an anonymous default whose empty editable set drops tiles silently.
    Seeding and migrations have no request, so one is fabricated for the admin
    arches installs. The verb is dropped either way: PATCH there means merge,
    and these are whole saves whichever verb brought the data in."""
    saving = copy(request) if request is not None else HttpRequest()
    saving.method = None
    if request is None:
        saving.user = get_user_model().objects.get(username="admin")
    return saving
