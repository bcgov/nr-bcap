"""GET user_profile: who the caller is, and whether the client should give them
the staff view. is_internal is answered here so the frontend never has to know
which group marks staff, nor that a superuser counts as one."""

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
        cls.url = reverse("bcap_user_profile")

    def get_profile(self, user):
        self.idir_login_simulate(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_returns_the_callers_name_and_groups(self):
        profile = self.get_profile(self.user)

        self.assertEqual(profile["username"], "testuser")
        self.assertEqual(profile["groups"], [Groups.SUBMITTER])

    def test_an_applicant_is_not_internal(self):
        self.assertIs(self.get_profile(self.user)["is_internal"], False)

    def test_an_archaeology_branch_member_is_internal(self):
        self.assertIs(self.get_profile(self.branch_member)["is_internal"], True)

    def test_a_superuser_is_internal_without_the_branch_group(self):
        # The group list alone would call them external, which is why the answer
        # is not left to the client to work out.
        profile = self.get_profile(self.superuser)

        self.assertNotIn(Groups.ARCHAEOLOGY_BRANCH, profile["groups"])
        self.assertIs(profile["is_internal"], True)

    def test_refuses_a_caller_holding_no_role(self):
        roleless = get_user_model().objects.create_user(
            username="roleless", password="pass"
        )
        self.idir_login_simulate(roleless)

        self.assertEqual(self.client.get(self.url).status_code, 403)
