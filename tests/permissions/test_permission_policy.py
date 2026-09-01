"""Check the graph permission policy against the checked-in graph JSON files.

A slug typo in the policy, or a newly added graph nobody assigned groups to,
both fail silently at runtime: the graph is skipped and default-deny hides it.
These tests need no database.
"""

import json
from pathlib import Path

from django.apps import apps
from django.test import SimpleTestCase

from bcap.permissions.graph_policy import (
    index_group_names,
    nodegroup_perms,
    policy_slugs,
)


def package_graph_slugs():
    graphs = Path(apps.get_app_config("bcap").path) / "pkg/graphs/resource_models"
    return {
        json.loads(path.read_text())["graph"][0]["slug"]
        for path in graphs.glob("*.json")
    }


class PermissionPolicyTests(SimpleTestCase):
    def test_policy_slugs_all_exist_as_graphs(self):
        unknown = set(policy_slugs()) - package_graph_slugs()
        self.assertEqual(unknown, set(), "Policy slugs matching no graph")

    def test_every_graph_has_a_policy(self):
        uncovered = package_graph_slugs() - set(policy_slugs())
        self.assertEqual(
            uncovered, set(), "Graphs with no permission policy (denied to everyone)"
        )

    def test_unknown_slugs_are_dropped(self):
        self.assertEqual(policy_slugs(["not-a-graph"]), [])

    def test_every_policy_verb_maps_to_a_nodegroup_perm(self):
        for slug in policy_slugs():
            # A verb with no guardian perm raises here.
            for name, perms in nodegroup_perms(slug).items():
                self.assertTrue(perms, f"{slug} grants {name} nothing")

    def test_an_unlisted_graph_grants_nothing(self):
        self.assertEqual(nodegroup_perms("not-a-graph"), {})
        self.assertEqual(
            index_group_names("not-a-graph"), {"groups_read": [], "groups_edit": []}
        )

    def test_the_index_never_promises_more_than_the_nodegroups(self):
        for slug in policy_slugs():
            perms = nodegroup_perms(slug)
            fields = index_group_names(slug)
            for name in fields["groups_read"]:
                self.assertIn("read_nodegroup", perms[name], f"{slug}: {name}")
            for name in fields["groups_edit"]:
                self.assertIn("write_nodegroup", perms[name], f"{slug}: {name}")
