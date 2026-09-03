"""Signed-in users must read as resource reviewers.

Arches parks a non-reviewer's tile save in provisionaledits and writes the tile
empty (Tile.save), and skips their deletes (TileModel.delete). BCAP has no
approval step, so losing this override silently drops applicants' data rather
than raising.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from bcap.permissions.bcap_arches_permission_framework import (
    ANONYMOUS_USERNAME,
    BcapArchesPermissionFramework,
)


class ResourceReviewerOverrideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.framework = BcapArchesPermissionFramework()
        cls.submitter = get_user_model().objects.create_user(
            username="submitter", password="pass"
        )
        cls.public, _ = get_user_model().objects.get_or_create(
            username=ANONYMOUS_USERNAME
        )

    def test_signed_in_user_without_groups_is_a_reviewer(self):
        self.assertTrue(self.framework.user_is_resource_reviewer(self.submitter))

    def test_public_user_is_not_a_reviewer(self):
        self.assertFalse(self.framework.user_is_resource_reviewer(self.public))

    def test_unauthenticated_user_is_not_a_reviewer(self):
        self.assertFalse(self.framework.user_is_resource_reviewer(AnonymousUser()))
