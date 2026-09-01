"""The applier's effect on guardian rows for one graph.

Checks the three things a policy reset has to get right: the grants match the
matrix, groups the policy omits are denied outright, and grants made outside the
policy do not survive.
"""

from django.contrib.auth.models import User
from django.core.cache import caches
from django.test import TestCase
from guardian.shortcuts import assign_perm, get_perms

from arches.app.models.models import Group, NodeGroup

from bcap.permissions.bcap_arches_permission_framework import (
    NO_ACCESS,
    BcapArchesPermissionFramework,
)
from bcap.permissions.graph_policy import nodegroup_perms
from bcap.permissions.groups import Groups
from bcap.util.bcap_aliases import GraphSlugs

SLUG = GraphSlugs.ARCHAEOLOGICAL_SITE


class ApplyPermissionDefaultsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nodegroups = list(
            NodeGroup.objects.filter(node__graph__slug=SLUG).distinct()
        )

    def setUp(self):
        if not self.nodegroups:
            self.skipTest(f"{SLUG} is not loaded in the test database")

    def test_grants_match_the_policy(self):
        BcapArchesPermissionFramework.apply_permission_defaults([SLUG])

        nodegroup = self.nodegroups[0]
        checked = 0
        for name, expected in nodegroup_perms(SLUG).items():
            group = Group.objects.filter(name=name).first()
            if group:
                checked += 1
                self.assertEqual(set(get_perms(group, nodegroup)), expected, name)
        self.assertTrue(checked, "no policy group exists to check against")

    def test_a_group_the_policy_omits_is_denied(self):
        BcapArchesPermissionFramework.apply_permission_defaults([SLUG])

        # Resource Editor holds model-level nodegroup perms and this graph does
        # not grant it, so it needs the denial to be kept out.
        editor = Group.objects.get(name=Groups.RESOURCE_EDITOR)
        self.assertEqual(get_perms(editor, self.nodegroups[0]), [NO_ACCESS])

    def test_grants_made_outside_the_policy_are_cleared(self):
        nodegroup = self.nodegroups[0]
        outsider = User.objects.create_user("policy-outsider")
        assign_perm("read_nodegroup", outsider, nodegroup)
        self.assertEqual(get_perms(outsider, nodegroup), ["read_nodegroup"])

        BcapArchesPermissionFramework.apply_permission_defaults([SLUG])

        self.assertEqual(get_perms(outsider, nodegroup), [])

    def test_the_permission_cache_is_cleared(self):
        cache = caches["user_permission"]
        cache.set("stale", {"NodeGroup": "whatever"})

        BcapArchesPermissionFramework.apply_permission_defaults([SLUG])

        self.assertIsNone(cache.get("stale"))
