"""Unit tests for ContributorDescriptors.

The class depends on GraphLookup (which hits the DB) and
BCPrimaryDescriptorsFunction.get_value_from_node (which queries TileModel).
Both are patched out so these tests are pure unit tests with no DB access.
"""

from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from bcap.functions.contributor_descriptors import ContributorDescriptors
from bcap.util.aliases.contributor import ContributorAliases as aliases


def _mock_node(label):
    node = MagicMock()
    node.name = label
    node.nodegroup_id = "test-ng-id"
    return node


class ContributorDescriptorsTest(SimpleTestCase):
    def setUp(self):
        # Prevent GraphLookup.__init__ from querying the DB.
        with patch("bcap.functions.contributor_descriptors.GraphLookup"):
            self.fn = ContributorDescriptors()

        self._nodes = {
            aliases.CONTRIBUTOR_NAME: _mock_node("Contributor Name"),
            aliases.FIRST_NAME: _mock_node("First Name"),
            aliases.CONTRIBUTOR_TYPE: _mock_node("Contributor Type"),
            aliases.CONTRIBUTOR_ROLE: _mock_node("Contributor Role"),
        }

        self.fn._graph_lookup = MagicMock()
        self.fn._graph_lookup.get_node.side_effect = lambda a: self._nodes[a]
        self.fn._graph_lookup.get_datatype.return_value = MagicMock()

    def _patch_values(self, values_by_alias):
        """Patch get_value_from_node to return controlled values keyed by alias."""
        node_to_value = {self._nodes[a]: v for a, v in values_by_alias.items()}

        patcher = patch.object(
            self.fn,
            "get_value_from_node",
            side_effect=lambda node, datatype, resource: node_to_value.get(node),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------

    def test_name_nodes_contains_contributor_name(self):
        self.assertIn(aliases.CONTRIBUTOR_NAME, ContributorDescriptors._name_nodes)

    def test_name_nodes_contains_first_name(self):
        self.assertIn(aliases.FIRST_NAME, ContributorDescriptors._name_nodes)

    def test_card_nodes_contains_contributor_type(self):
        self.assertIn(aliases.CONTRIBUTOR_TYPE, ContributorDescriptors._card_nodes)

    def test_card_nodes_contains_contributor_role(self):
        self.assertIn(aliases.CONTRIBUTOR_ROLE, ContributorDescriptors._card_nodes)

    # ------------------------------------------------------------------
    # Name descriptor
    # ------------------------------------------------------------------

    def test_name_with_both_names_joins_with_comma(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_NAME: "Smith",
                aliases.FIRST_NAME: "John",
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="name"
        )
        self.assertEqual(result, "Smith, John")

    def test_name_without_first_name_returns_contributor_name_only(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_NAME: "Smith",
                aliases.FIRST_NAME: None,
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="name"
        )
        self.assertEqual(result, "Smith")

    def test_name_with_empty_first_name_omits_comma(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_NAME: "Smith",
                aliases.FIRST_NAME: "",
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="name"
        )
        self.assertEqual(result, "Smith")

    def test_name_with_no_values_returns_empty_string(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_NAME: None,
                aliases.FIRST_NAME: None,
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="name"
        )
        self.assertEqual(result, "")

    # ------------------------------------------------------------------
    # Card / description descriptor
    # ------------------------------------------------------------------

    def test_card_includes_both_values(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_TYPE: "External",
                aliases.CONTRIBUTOR_ROLE: "Principal Investigator",
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="description"
        )
        self.assertIn("External", result)
        self.assertIn("Principal Investigator", result)

    def test_card_includes_node_labels(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_TYPE: "External",
                aliases.CONTRIBUTOR_ROLE: "Principal Investigator",
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="description"
        )
        self.assertIn("Contributor Type", result)
        self.assertIn("Contributor Role", result)

    def test_card_omits_node_when_value_is_empty(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_TYPE: "External",
                aliases.CONTRIBUTOR_ROLE: None,
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="description"
        )
        self.assertIn("External", result)
        self.assertNotIn("Contributor Role", result)

    def test_card_returns_empty_string_when_all_values_absent(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_TYPE: None,
                aliases.CONTRIBUTOR_ROLE: None,
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="description"
        )
        self.assertEqual(result, "")

    # ------------------------------------------------------------------
    # map_popup descriptor (same card-node path as description)
    # ------------------------------------------------------------------

    def test_map_popup_uses_card_nodes(self):
        self._patch_values(
            {
                aliases.CONTRIBUTOR_TYPE: "Internal",
                aliases.CONTRIBUTOR_ROLE: "Permit Holder",
            }
        )
        result = self.fn.get_primary_descriptor_from_nodes(
            "res-id", {}, descriptor="map_popup"
        )
        self.assertIn("Internal", result)
        self.assertIn("Permit Holder", result)
