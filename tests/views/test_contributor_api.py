"""GET api/contributors/assignable: the Contributors staff can assign work to.
Editor-only, and only Contributors with a login are offered (an applicant with
no account can't be handed a requirement)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.builders.contributor_builder import ContributorSpec
from bcap.util.controlled_list import reference_value
from tests.builders import FixtureBuilder

from tests.controlled_list_fixtures import ControlledListFixtures
from tests.views.helpers import AuthTestHelper


@override_settings(ROOT_URLCONF="tests.test_urls")
class AssignableContributorsTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # creates cls.user, who holds no role
        ControlledListFixtures.seed()
        cls.editor = get_user_model().objects.create_user(
            username="assign-editor", password="pass"
        )
        cls.editor.groups.add(Group.objects.get(name="Resource Editor"))

        builder = FixtureBuilder()
        contributor_type = reference_value("contributor", "contributor_type")
        cls.linked = builder.make_contributor(
            ContributorSpec(contributor_type, "Grace", "Hopper", bcap_username="grace")
        )
        cls.also_linked = builder.make_contributor(
            ContributorSpec(contributor_type, "Alan", "Turing", bcap_username="alan")
        )
        # No login, so nothing can be assigned to them.
        cls.unlinked = builder.make_contributor(
            ContributorSpec(contributor_type, "Uma", "Unlinked")
        )
        cls.url = reverse("assignable_contributors")

    def test_lists_the_login_linked_contributors_name_sorted(self):
        self.idir_login_simulate(self.editor)

        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(
            [option["id"] for option in body],
            [str(self.linked.pk), str(self.also_linked.pk)],
        )
        self.assertEqual(body[0]["name"], "Hopper, Grace")

    def test_excludes_contributors_without_a_login(self):
        self.idir_login_simulate(self.editor)

        ids = [option["id"] for option in self.client.get(self.url).json()]

        self.assertNotIn(str(self.unlinked.pk), ids)

    def test_requires_a_resource_editor(self):
        self.idir_login_simulate(self.user)  # authenticated, but no role
        self.assertEqual(self.client.get(self.url).status_code, 403)

        self.client.logout()
        # Anonymous never reaches the view: auth middleware bounces it to login.
        self.assertEqual(self.client.get(self.url).status_code, 302)
