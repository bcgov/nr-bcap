from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.models import RegistrationLink
from bcap.permissions.groups import SELF_MANAGE_ROLE_GROUPS
from bcap.services.contributor.contributor_service import ContributorService
from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder

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
        self.builder = FixtureBuilder()
        self.contributor_type = reference_value("contributor", "contributor_type")
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
        alan = self.make_contributor("Turing", first_name="Alan", bcap_username="at")
        self.idir_login_simulate(self.admin)
        resp = self.client.get(reverse("unlinked_contributors"))
        self.assertEqual(resp.status_code, 200)
        ids = [o["id"] for o in resp.json()]
        self.assertIn(str(grace.pk), ids)
        self.assertNotIn(str(alan.pk), ids)
        narrowed = self.client.get(reverse("unlinked_contributors"), {"search": "zzz"})
        self.assertEqual(narrowed.json(), [])

    def test_issue_link_stores_whitelisted_groups(self):
        contributor = self.make_contributor()
        self.idir_login_simulate(self.admin)
        resp = self.client.post(
            reverse("registration_link"),
            {
                "contributor_id": str(contributor.pk),
                "groups": ["Permit Reviewer"],
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(RegistrationLink.objects.get().groups, ["Permit Reviewer"])

    def test_issue_link_rejects_a_non_whitelisted_group(self):
        contributor = self.make_contributor()
        self.idir_login_simulate(self.admin)
        resp = self.client.post(
            reverse("registration_link"),
            {
                "contributor_id": str(contributor.pk),
                "groups": ["Resource Editor"],
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(RegistrationLink.objects.exists())

    def test_issue_link_new_contributor_includes_phone(self):
        self.idir_login_simulate(self.admin)
        resp = self.client.post(
            reverse("registration_link"),
            {
                "new_contributor": {
                    "name": "Hopper",
                    "first_name": "Grace",
                    "email": "grace@example.com",
                    "phone": "250-555-0100",
                }
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            RegistrationLink.objects.get().new_contributor["phone"], "250-555-0100"
        )

    def test_assignable_groups_lists_the_whitelist_for_admins(self):
        self.idir_login_simulate(self.admin)
        resp = self.client.get(reverse("assignable_groups"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), SELF_MANAGE_ROLE_GROUPS)

    def test_assignable_groups_requires_admin(self):
        self.idir_login_simulate(self.user)
        self.assertEqual(self.client.get(reverse("assignable_groups")).status_code, 403)

    def test_claim_get_stashes_token_and_redirects_to_login(self):
        resp = self.client.get(reverse("registration_claim"), {"token": "abc-123"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers["Location"], reverse("auth"))
        self.assertEqual(
            self.client.session.get("pending_registration_token"), "abc-123"
        )
