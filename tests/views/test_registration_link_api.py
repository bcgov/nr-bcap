from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.models import RegistrationLink
from bcap.services.dashboard.contributor_service import ContributorService
from bcap.util.dashboard.resource_builder import ContributorSpec, ResourceBuilder

from tests.controlled_list_fixtures import ControlledListFixtures
from tests.views.helpers import AuthTestHelper


@override_settings(
    ROOT_URLCONF="tests.test_urls",
    PUBLIC_SERVER_ADDRESS="https://bcap.test/bcap",
)
class RegistrationLinkApiTest(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # creates cls.user (a non-staff member)
        ControlledListFixtures.seed()
        cls.admin = get_user_model().objects.create_user(
            username="reg_admin", password="pw", is_staff=True
        )

    def setUp(self):
        super().setUp()
        self.builder = ResourceBuilder()
        self.contributor_type = self.builder.reference_value(
            "contributor", "contributor_type"
        )
        self.contributors = ContributorService()

    def make_contributor(self, name="Hopper", first_name="Grace", **kwargs):
        spec = ContributorSpec(self.contributor_type, first_name, name, **kwargs)
        return self.builder.make_contributor(spec)

    def test_issue_link_requires_admin(self):
        # An authenticated but non-staff user is forbidden.
        self.idir_login_simulate(self.user)
        resp = self.client.post(
            reverse("registration_link"), {}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_issue_link_for_existing_contributor(self):
        contributor = self.make_contributor()
        self.idir_login_simulate(self.admin)
        resp = self.client.post(
            reverse("registration_link"),
            {"contributor_id": str(contributor.pk)},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        link = RegistrationLink.objects.get()
        self.assertEqual(str(link.contributor_id), str(contributor.pk))
        self.assertEqual(
            resp.json()["signup_url"],
            f"https://bcap.test/bcap/signup/claim?token={link.id}",
        )

    def test_issue_link_for_new_contributor_defers_creation(self):
        self.idir_login_simulate(self.admin)
        payload = {
            "new_contributor": {
                "name": "Hopper",
                "first_name": "Grace",
                "email": "grace@example.com",
            }
        }
        resp = self.client.post(
            reverse("registration_link"), payload, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 201)
        link = RegistrationLink.objects.get()
        self.assertIsNone(link.contributor_id)
        self.assertEqual(link.new_contributor["email"], "grace@example.com")

    def test_issue_link_requires_exactly_one_target(self):
        self.idir_login_simulate(self.admin)
        resp = self.client.post(
            reverse("registration_link"), {}, content_type="application/json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_unlinked_contributors_list_and_search(self):
        grace = self.make_contributor()
        self.make_contributor("Turing", first_name="Alan", bcap_username="at")
        self.idir_login_simulate(self.admin)
        resp = self.client.get(reverse("unlinked_contributors"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([o["id"] for o in resp.json()], [str(grace.pk)])
        narrowed = self.client.get(reverse("unlinked_contributors"), {"search": "zzz"})
        self.assertEqual(narrowed.json(), [])

    def test_claim_get_stashes_token_and_redirects_to_login(self):
        resp = self.client.get(reverse("registration_claim"), {"token": "abc-123"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], reverse("auth"))
        self.assertEqual(
            self.client.session.get("pending_registration_token"), "abc-123"
        )
