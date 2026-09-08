"""What an applicant may reach of the arches ecosystem.

The gate answers per request, so these ask the URL table rather than the
allow-list: a route added or renamed upstream is covered without anyone
remembering to list it here.
"""

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, URLResolver, get_resolver, resolve, reverse

from bcap.permissions.applicant_gate import ArchesDefaultDenyApplicantGate as gate
from bcap.permissions.groups import Groups
from bcap.util.bcap_aliases import GraphSlugs
from tests.builders import FixtureBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.services.contributor_fixtures import make_contributor
from tests.views.helpers import AuthTestHelper


def gated_arches_routes():
    """URLs of the argless routes the gate keeps applicants off, judged by the
    view that actually serves each one: BCAP shadows several arches routes with
    its own, and those answer for themselves."""
    stack = [get_resolver(settings.ROOT_URLCONF)]
    seen = set()
    while stack:
        for pattern in stack.pop().url_patterns:
            if isinstance(pattern, URLResolver):
                stack.append(pattern)
                continue
            if not pattern.name or pattern.pattern.regex.groups:
                continue
            try:
                url = reverse(pattern.name)
            except NoReverseMatch:
                # Namespaced routes (oauth2, admin) need their prefix; none of
                # them is served by a governed package.
                continue
            if url in seen:
                continue
            seen.add(url)
            module = resolve(url).func.__module__
            if module.startswith(gate.GOVERNED_PACKAGES) and not module.startswith(
                gate.APPLICANT_ALLOWED
            ):
                yield url


@override_settings(ROOT_URLCONF="tests.test_urls")
class TestArchesDefaultDenyApplicantGate(AuthTestHelper, TestCase):
    """Applicants reach only the arches core views the permit app needs, so the
    gate holds wherever an upgrade moves a route or adds one."""

    def test_applicant_is_denied_gated_routes(self):
        """Walk what is registered rather than trusting a list, so a route added
        upstream is checked too. Search terms is the one that mattered: it
        answers from nodegroup permissions, which an applicant holds graph-wide,
        and would otherwise offer up other applicants' descriptors."""
        self.idir_login_simulate()
        routes = set(gated_arches_routes())
        self.assertIn(reverse("search_terms"), routes)
        for route in routes:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 403)

    def test_applicant_is_denied_the_generic_resource_routes(self):
        """These carry no owner filter, so a list call would return every
        applicant's resources. The typed BCAP routes are the way in."""
        self.idir_login_simulate()
        for name, kwargs in (
            ("arches_querysets:api-resources", {"graph": "permit_application"}),
            (
                "arches_querysets:api-tiles",
                {"graph": "permit_application", "nodegroup_alias": "permit_details"},
            ),
        ):
            with self.subTest(route=name):
                response = self.client.get(reverse(name, kwargs=kwargs))
                self.assertEqual(response.status_code, 403)

    def test_applicant_keeps_the_views_the_permit_app_needs(self):
        self.idir_login_simulate()
        self.assertNotEqual(
            self.client.get(reverse("user_profile_manager")).status_code, 403
        )

    def test_internal_user_reaches_search(self):
        self.user.groups.add(Group.objects.get(name=Groups.ARCHAEOLOGY_BRANCH))
        self.idir_login_simulate()
        self.assertEqual(self.client.get(reverse("search_home")).status_code, 200)


@override_settings(ROOT_URLCONF="tests.test_urls")
class TestRelatableResourcePicker(AuthTestHelper, TestCase):
    """The picker lists every instance of whatever graphs its node names, so an
    applicant reaches it only where that is contributors."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()
        builder = FixtureBuilder()
        cls.contributor = make_contributor(builder, "Acme Corp")
        cls.off_graph = builder.make_resource(GraphSlugs.INVESTIGATION)

    def picker(self, graph, node_alias, **params):
        return self.client.get(
            reverse(
                "arches_vue_components:api-relatable-resources",
                kwargs={"graph": graph, "node_alias": node_alias},
            ),
            params,
        )

    def test_applicant_may_pick_a_contributor(self):
        self.idir_login_simulate()
        response = self.picker("permit_application", "application_proponent")
        self.assertNotEqual(response.status_code, 403)

    def test_applicant_may_carry_a_contributor_as_the_current_value(self):
        self.idir_login_simulate()
        response = self.picker(
            "permit_application",
            "application_proponent",
            initialValue=str(self.contributor.pk),
        )
        self.assertNotEqual(response.status_code, 403)

    def test_applicant_may_not_name_an_off_graph_current_value(self):
        # The picker answers with the descriptor of whatever initialValue names,
        # ahead of the candidates it was asked for.
        self.idir_login_simulate()
        response = self.picker(
            "permit_application",
            "application_proponent",
            initialValue=str(self.off_graph.pk),
        )
        self.assertEqual(response.status_code, 403)

    def test_applicant_may_not_pick_a_permit(self):
        self.idir_login_simulate()
        self.assertEqual(
            self.picker("permit_application", "concurrent_permits_list").status_code,
            403,
        )

    def test_applicant_may_not_pick_a_site(self):
        self.idir_login_simulate()
        self.assertEqual(
            self.picker("archaeological_site", "parent_site").status_code, 403
        )


@override_settings(ROOT_URLCONF="tests.test_urls")
class TestBcapRoutesOutsideTheGate(AuthTestHelper, TestCase):
    """BCAP's own views are not governed by the gate, so the ones that shadow a
    staff-only arches page answer for themselves."""

    def test_applicant_is_denied_the_edit_history_page(self):
        """It lists the last 1000 edits across every resource."""
        self.idir_login_simulate()
        self.assertEqual(self.client.get(reverse("edit_history")).status_code, 403)
