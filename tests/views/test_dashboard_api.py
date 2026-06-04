from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.util.enums import DashboardStatus
from tests.controlled_list_fixtures import ControlledListFixtures
from tests.services.test_dashboard_service import build_permit_graph
from tests.views.helpers import AuthTestHelper


@override_settings(ROOT_URLCONF="tests.test_urls")
class DashboardViewAuthTests(AuthTestHelper, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("dashboard")

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
        self.url = reverse("dashboard")
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
        # ASSIGNED_TO_ME matches the permit. She also belongs to Acme, so
        # ASSIGNED_TO_ASSOCIATED_COMPANIES matches it too.
        for status in (
            DashboardStatus.ASSIGNED_TO_ME,
            DashboardStatus.ASSIGNED_TO_ASSOCIATED_COMPANIES,
        ):
            with self.subTest(status=status):
                resp = self.client.get(self.url, {"status": status})
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
