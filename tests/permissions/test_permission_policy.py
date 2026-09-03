"""Check PERMISSION_DEFAULTS against the checked-in graph JSON files.

A stale graph id in the setting, or a newly added graph nobody granted access
to, both fail silently at runtime: the graph is skipped and default deny hides
it. These tests need no database.
"""

import json
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase

RESOURCE_INSTANCE_PERMS = {
    "view_resourceinstance",
    "change_resourceinstance",
    "add_resourceinstance",
    "delete_resourceinstance",
    "no_access_to_resourceinstance",
}


def package_graphs():
    """Graph id to slug, for every resource model in the package."""
    graphs = Path(apps.get_app_config("bcap").path) / "pkg/graphs/resource_models"
    return {
        json.loads(path.read_text())["graph"][0]["graphid"]: json.loads(
            path.read_text()
        )["graph"][0]["slug"]
        for path in graphs.glob("*.json")
    }


class PermissionDefaultsTests(SimpleTestCase):
    def test_every_graph_granted_exists(self):
        unknown = set(settings.PERMISSION_DEFAULTS) - set(package_graphs())
        self.assertEqual(unknown, set(), "Graph ids matching no graph")

    def test_every_graph_is_granted(self):
        graphs = package_graphs()
        uncovered = {
            graphs[graph_id]
            for graph_id in set(graphs) - set(settings.PERMISSION_DEFAULTS)
        }
        self.assertEqual(
            uncovered, set(), "Graphs with no defaults (denied to everyone)"
        )

    def test_every_permission_granted_is_a_real_one(self):
        """A codename arches does not know is granted to nobody, silently."""
        for graph_id, grants in settings.PERMISSION_DEFAULTS.items():
            for grant in grants:
                unknown = set(grant["permissions"]) - RESOURCE_INSTANCE_PERMS
                self.assertEqual(unknown, set(), graph_id)

    def test_every_grant_names_a_group(self):
        for graph_id, grants in settings.PERMISSION_DEFAULTS.items():
            for grant in grants:
                self.assertEqual(grant["type"], "group", graph_id)
