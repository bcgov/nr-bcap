"""GET user_profile: who the caller is. The client decides from the group list
and is_superuser whether to show the staff view."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from bcap.permissions.groups import Groups
from tests.views.helpers import AuthTestHelper


@override_settings(ROOT_URLCONF="tests.test_urls")
class UserProfileTests(AuthTestHelper, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # cls.user is an external applicant
        User = get_user_model()
        cls.branch_member = User.objects.create_user(
            username="branch-member", password="pass"
        )
        cls.branch_member.groups.add(Group.objects.get(name=Groups.ARCHAEOLOGY_BRANCH))
        cls.superuser = User.objects.create_superuser(
            username="profile-admin", password="pass", email="admin@example.com"
        )
        cls.superuser.groups.add(Group.objects.get(name=Groups.SUBMITTER))
        cls.url = reverse("bcap_api_user")

    def get_profile(self, user):
        self.idir_login_simulate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_returns_the_callers_name_and_groups(self):
        profile = self.get_profile(self.user)

        self.assertEqual(profile["username"], "testuser")
        self.assertEqual(list(profile["groups"]), [Groups.SUBMITTER])
        self.assertIs(profile["is_superuser"], False)

    def test_reports_the_group_that_marks_staff(self):
        profile = self.get_profile(self.branch_member)

        self.assertIn(Groups.ARCHAEOLOGY_BRANCH, profile["groups"])

    def test_reports_a_superuser_without_the_branch_group(self):
        # The group list alone would call them external, which is why the client
        # is given is_superuser as well.
        profile = self.get_profile(self.superuser)

        self.assertNotIn(Groups.ARCHAEOLOGY_BRANCH, profile["groups"])
        self.assertIs(profile["is_superuser"], True)

    def test_refuses_a_caller_holding_no_role(self):
        roleless = get_user_model().objects.create_user(
            username="roleless", password="pass"
        )
        self.idir_login_simulate(roleless)

        self.assertEqual(self.client.get(self.url).status_code, 403)
