"""Route-layer guards: anonymous is redirected off every owned route, and
low-privilege roles (Guest, Submitter) are denied at the gate bar an allowlist.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse

from arches.app.models.models import Group

from bcap.permissions.groups import Groups

FAR_FUTURE = 9999999999  # epoch seconds, past any test run
_UUID = "00000000-0000-0000-0000-000000000000"
SAMPLE_BY_CONVERTER = {"UUIDConverter": _UUID, "IntConverter": "1"}
PUBLIC_ROUTE_NAMES = set()


def _sample_kwargs(pattern):
    # path() params carry typed converters; re_path() (MVT) only named groups.
    converters = getattr(pattern.pattern, "converters", None)
    if converters:
        return {
            name: SAMPLE_BY_CONVERTER.get(type(conv).__name__, "x")
            for name, conv in converters.items()
        }
    names = pattern.pattern.regex.groupindex
    return {name: _UUID if name == "nodeid" else "1" for name in names}


def _walk(patterns):
    for entry in patterns:
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns)
        elif isinstance(entry, URLPattern):
            yield entry


def _owned_routes():
    """(name, url) for every route backed by a bcap.views view."""
    for pattern in _walk(get_resolver().url_patterns):
        cb = pattern.callback
        view = getattr(cb, "cls", None) or getattr(cb, "view_class", cb)
        if not getattr(view, "__module__", "").startswith("bcap.views"):
            continue
        if pattern.name in PUBLIC_ROUTE_NAMES:
            continue
        url = reverse(pattern.name, kwargs=_sample_kwargs(pattern))
        yield pattern.name, url


class AnonymousRouteAccessTests(TestCase):
    def test_owned_routes_redirect_anonymous(self):
        for name, url in _owned_routes():
            code = self.client.get(url).status_code
            self.assertEqual(code, 302, f"{name} -> {url}")


# Routes each low-priv role may reach past the gate; trim one to fail the test.
LOW_PRIV_ALLOWLIST = {
    Groups.GUEST: {
        "bcap_user_profile",
    },
    Groups.SUBMITTER: {
        "bcap_user_profile",
        "dashboard_external",
        "hca_permit_list",
        "hca_permit",
        "permit_application",
        "permit_application_create",
        "resource_draft_list_create",
        "resource_draft_detail",
    },
}

# Denied AT THE GATE. Anything else (200/404/405/...) means the role reached
# the view -- a 404 from owner-scoping still means it was allowed in.
GATE_BLOCKED = {301, 302, 401, 403}


class LowPrivilegeRouteAccessTests(TestCase):
    """Guest and Submitter must be denied at the gate (302/403) on every owned
    route except their allowlist; getting past the gate trips this."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.users = {}
        for role in (Groups.GUEST, Groups.SUBMITTER):
            group, _ = Group.objects.get_or_create(name=role)
            user = User.objects.create_user(role.replace(" ", "_").lower())
            user.groups.add(group)
            cls.users[role] = user

    def _login(self, user):
        # The auth middleware logs out token-less sessions; plant a token.
        self.client.force_login(user)
        session = self.client.session
        session["oauth_token"] = {"expires_at": FAR_FUTURE}
        session.save()

    def _assert_least_privilege(self, role):
        self._login(self.users[role])
        allowed = LOW_PRIV_ALLOWLIST[role]
        leaks = {
            name: code
            for name, url in _owned_routes()
            if (code := self.client.get(url).status_code) not in GATE_BLOCKED
            and name not in allowed
        }
        self.assertEqual(leaks, {}, f"{role} got past the gate on: {leaks}")

    def test_guest_reaches_only_allowlisted_routes(self):
        self._assert_least_privilege(Groups.GUEST)

    def test_submitter_reaches_only_allowlisted_routes(self):
        self._assert_least_privilege(Groups.SUBMITTER)
