"""Staff and applicants must read as resource reviewers.

Arches parks a non-reviewer's tile save in provisionaledits and writes the tile
empty (Tile.save), and skips their deletes (TileModel.delete). BCAP has no
approval step, so losing this override silently drops applicants' data rather
than raising.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase

from bcap.permissions.bcap_arches_permission_framework import (
    ANONYMOUS_USERNAME,
    BcapArchesPermissionFramework,
)
from bcap.permissions.groups import Groups


class ResourceReviewerOverrideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.framework = BcapArchesPermissionFramework()
        cls.submitter = get_user_model().objects.create_user(
            username="submitter", password="pass"
        )
        cls.submitter.groups.add(Group.objects.get(name=Groups.SUBMITTER))
        cls.stranger = get_user_model().objects.create_user(
            username="stranger", password="pass"
        )
        cls.public, _ = get_user_model().objects.get_or_create(
            username=ANONYMOUS_USERNAME
        )

    def test_who_reviews(self):
        # Group membership does not decide this: a non-reviewer's tile save lands
        # in provisionaledits with the tile written empty, so narrowing it by
        # role would lose that role's edits silently.
        for name, expected, user in (
            ("a submitter", True, self.submitter),
            ("a signed-in user in no group", True, self.stranger),
            ("the public user", False, self.public),
            ("an unauthenticated user", False, AnonymousUser()),
        ):
            with self.subTest(name):
                reviewer = self.framework.user_is_resource_reviewer(user)
                self.assertIs(bool(reviewer), expected)
