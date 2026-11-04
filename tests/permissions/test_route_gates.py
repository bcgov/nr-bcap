"""That every route BCAP serves itself decides who may call it.

The applicant gate governs the arches ecosystem; BCAP's own routes answer for
themselves, and a view added without a gate is reachable by anyone with a
session. These walk the URL table rather than a list, so a route added
tomorrow is covered.

A DRF view is judged by what it declares, since its permission class runs
before the handler. A plain Django view ignores permission_classes entirely, so
it is judged by what it does with a caller holding no role.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, URLResolver, get_resolver, resolve, reverse

from rest_framework.permissions import AllowAny

from tests.views.helpers import login_as

PLACEHOLDER_UUID = "12345678-1234-1234-1234-123456789abc"
TILE_COORDS = ("zoom", "x", "y")

# Reachable without a role by design. Everything else has to refuse one.
UNGATED_BY_DESIGN = {
    # Redeems the signup token and bounces the visitor into login, so it runs
    # before anyone has a role at all.
    "registration_claim",
    # The identity provider's return leg, which is what establishes the session.
    "auth_callback",
    "external_oauth_callback",
    # Proxies the public BC government basemaps for any session; its own check
    # narrows the sources that read the app database. Left out because calling
    # it would reach upstream.
    "bcap_tile_server",
    "bcap_tile_server_root",
}


def placeholder(name, converter):
    """A URL argument that reverses, without needing the row to exist."""
    if name in TILE_COORDS or type(converter).__name__ == "IntConverter":
        return "1"
    if converter is not None and type(converter).__name__ != "UUIDConverter":
        return "x"
    return PLACEHOLDER_UUID


def bcap_routes():
    """Every route served by a view of BCAP's own, with arguments filled in."""
    stack = [get_resolver(settings.ROOT_URLCONF)]
    seen = set()
    while stack:
        for pattern in stack.pop().url_patterns:
            if isinstance(pattern, URLResolver):
                stack.append(pattern)
                continue
            if not pattern.name or pattern.name in seen:
                continue
            converters = getattr(pattern.pattern, "converters", {}) or {}
            kwargs = {
                name: placeholder(name, converters.get(name))
                for name in pattern.pattern.regex.groupindex
            }
            try:
                url = reverse(pattern.name, kwargs=kwargs)
            except NoReverseMatch:
                # Namespaced and unnamed-argument routes; none is BCAP's own.
                continue
            view = resolve(url).func
            if view.__module__.startswith("bcap."):
                seen.add(pattern.name)
                yield pattern.name, url, getattr(view, "cls", None) or getattr(
                    view, "view_class", None
                )


@override_settings(ROOT_URLCONF="tests.test_urls")
class RouteGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # No groups: past the session check, holding nothing.
        cls.stranger = get_user_model().objects.create_user("route-gate-stranger")

    def test_every_route_declares_or_refuses(self):
        self.assertGreater(len(list(bcap_routes())), 20, "the walk found nothing")

    def test_drf_views_declare_a_permission_class(self):
        """Empty permission_classes falls back to the project default, and
        AllowAny opts out of it; both read as an oversight rather than a
        decision, so neither is allowed to pass silently."""
        for name, _, view_class in bcap_routes():
            declared = getattr(view_class, "permission_classes", None)
            if declared is None:
                continue
            with self.subTest(name):
                self.assertTrue(declared, "no permission class")
                if name not in UNGATED_BY_DESIGN:
                    self.assertNotIn(AllowAny, declared)

    def test_plain_django_views_refuse_a_caller_with_no_role(self):
        """These ignore permission_classes, so a missing decorator leaves them
        open to any session. A refusal is 403, or a redirect to login where the
        decorator was given no raise_exception."""
        login_as(self.client, self.stranger)
        for name, url, view_class in bcap_routes():
            if getattr(view_class, "permission_classes", None) is not None:
                continue
            if name in UNGATED_BY_DESIGN:
                continue
            with self.subTest(name):
                self.assertIn(self.client.get(url).status_code, (302, 403))


class AuthExemptPagesTests(TestCase):
    """The paths reachable without signing in at all.

    Every other layer sits behind the session check, so an addition here is the
    one change that can open a route by itself. Frozen rather than described:
    the point is that a new entry has to be argued for in review.
    """

    EXPECTED = {
        "/bcap",
        "/bcap/",
        "/unauthorized",
        "/bcap/index.htm",
        "/bcap/auth",
        "/bcap/auth/eoauth_start",
        "/bcap/auth/eoauth_cb",
        "/bcap/o/token",
        "/bcap/auth/user_profile",
        "/bcap/signup/claim",
    }

    def test_the_exempt_list_is_what_we_expect(self):
        exempt = settings.AUTHLIB_OAUTH_CLIENTS["default"]["urls"]["auth_exempt_pages"]

        self.assertEqual(set(exempt), self.EXPECTED)
