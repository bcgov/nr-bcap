from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.models.resource_draft import ResourceDraft
from bcap.services.dashboard.dashboard_types import (
    ExternalDashboardStatus,
    InternalDashboardStatus,
)
from bcap.util.dashboard.resource_builder import ResourceBuilder
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.services.test_dashboard_service import build_permit_graph
from tests.services.test_external_dashboard_service import build_external_permit
from tests.views.helpers import AuthTestHelper


@override_settings(ROOT_URLCONF="tests.test_urls")
class DashboardViewAuthTests(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dashboard_internal")

    def test_get_unauthenticated(self):
        # No session or token
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        # Fake token
        resp = self.client.get(
            self.url,
            HTTP_AUTHORIZATION="Bearer ABC123",
        )
        self.assertEqual(resp.status_code, 302)


@override_settings(ROOT_URLCONF="tests.test_urls")
class DashboardViewCardsTests(AuthTestHelper, TestCase):
    """The dashboard endpoint end to end: view -> serializer -> service, against
    a real permit graph and an authenticated session."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Rolled back with the class transaction.
        ControlledListFixtures.seed()
        graph = build_permit_graph()
        cls.permit_id = str(graph.permit.pk)
        cls.ada_id = str(graph.ada.pk)
        cls.grace_id = str(graph.grace.pk)
        cls.acme_id = str(graph.acme.pk)

    def setUp(self):
        super().setUp()
        self.url = reverse("dashboard_internal")
        self.idir_login_simulate()

    def test_get_returns_serialized_card(self):
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(body["results"]), 1)
        card = body["results"][0]
        self.assertEqual(card["id"], self.permit_id)
        self.assertEqual(card["project_name"], "My Project")
        self.assertEqual(card["application_number"], "APP-1")
        # "Review" is satisfied, so the card surfaces "Field Assessment".
        self.assertEqual(card["requirement_name"], "Field Assessment")
        self.assertEqual(card["ministry_assignee_name"], "Grace Hopper")

    def test_get_filters_by_assignment_status(self):
        # Grace's bcap_username is the session user "testuser" and she is the
        # assignee of the active ("Field Assessment") requirement, so
        # ASSIGNED_TO_ME matches the permit.
        resp = self.client.get(
            self.url, {"status": InternalDashboardStatus.ASSIGNED_TO_ME}
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual([c["id"] for c in body["results"]], [self.permit_id])

    def test_limit_and_page_slice_results(self):
        # One permit on page 1; count is the total and the page/limit echo back.
        resp = self.client.get(self.url, {"limit": 1, "page": 1})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["limit"], 1)
        self.assertEqual(body["page"], 1)
        self.assertEqual([c["id"] for c in body["results"]], [self.permit_id])

        # Page 2 is past the end: empty results, total still reported.
        resp = self.client.get(self.url, {"limit": 1, "page": 2})
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"], [])

    def test_invalid_params_return_400(self):
        bad_params = [
            {"limit": 0},  # below minimum
            {"limit": 101},  # above maximum
            {"page": 0},  # below minimum
            {"limit": "not-a-number"},  # non-integer
            {"status": "BOGUS"},  # unknown status
        ]
        for params in bad_params:
            with self.subTest(params=params):
                resp = self.client.get(self.url, params)
                self.assertEqual(resp.status_code, 400)


@override_settings(ROOT_URLCONF="tests.test_urls")
class ExternalDashboardViewAuthTests(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dashboard_external")

    def test_get_unauthenticated_redirects(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)


@override_settings(ROOT_URLCONF="tests.test_urls")
class ExternalDashboardViewCardsTests(AuthTestHelper, TestCase):
    """The external dashboard endpoint end to end: view -> serializer ->
    service, scoped to the authenticated user's own applications and drafts."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ControlledListFixtures.seed()
        builder = ResourceBuilder()
        # Owned by the session user (testuser), so the created-by scope matches.
        cls.mine = build_external_permit(builder, "My App", cls.user, "Active")
        cls.draft = ResourceDraft.objects.create(
            user=cls.user,
            graph_slug="permit_application",
            data={
                "aliased_data": {
                    "application_identification": {
                        "aliased_data": {
                            "project_name": {"en": {"value": "Draft Project"}},
                        }
                    }
                }
            },
        )

    def setUp(self):
        super().setUp()
        self.url = reverse("dashboard_external")
        self.idir_login_simulate()

    def test_get_defaults_to_the_users_own_applications(self):
        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual([c["id"] for c in body["results"]], [str(self.mine.pk)])
        card = body["results"][0]
        self.assertEqual(card["project_name"], "My App")
        self.assertEqual(card["status"], "Permit Active")
        self.assertFalse(card["is_draft"])

    def test_drafts_scope_returns_the_users_drafts(self):
        resp = self.client.get(self.url, {"status": ExternalDashboardStatus.DRAFTS})

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual([c["id"] for c in body["results"]], [str(self.draft.id)])
        self.assertTrue(body["results"][0]["is_draft"])

    def test_invalid_status_returns_400(self):
        # The external status enum differs from the internal one, so an
        # internal-only value is rejected here.
        resp = self.client.get(
            self.url, {"status": InternalDashboardStatus.ASSIGNED_TO_ME}
        )
        self.assertEqual(resp.status_code, 400)
