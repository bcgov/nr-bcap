"""
Unit tests for BCAPSiteDescriptors.

A DB-backed test would need the graph's required legislative_act card satisfied
first, which costs more setup than the stubs in DescriptorTestCase.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase

from bcap.functions.bcap_site_descriptors import BCAPSiteDescriptors
from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases as A
from tests.functions.descriptor_helpers import DescriptorTestCase


class SiteDescriptorTestCase(DescriptorTestCase):
    descriptor_class = BCAPSiteDescriptors
    node_names = {
        A.DECISION_REGISTRATION_STATUS: "Raw Status Node Name",
        A.NAME: "Site Name",
        A.BORDEN_NUMBER: "Borden Number",
    }

    def setUp(self):
        super().setUp()
        # Derived from the typology_class tiles rather than read off a node.
        self.typologies: tuple[list, list] = ([], [])
        self.stub("_get_typologies", side_effect=lambda *a, **kw: self.typologies)


class TestDescriptorDispatch(SiteDescriptorTestCase):
    """The base dispatches on the descriptor argument, not config["type"]."""

    def test_name_descriptor_delegates_to_get_site_name(self):
        resource = MagicMock()
        mock_name = self.stub("_get_site_name", return_value="DjRi-123")
        result = self.fn.get_primary_descriptor_from_nodes(
            resource, config={}, descriptor="name"
        )
        assert result == "DjRi-123"
        assert mock_name.call_args.args[0] is resource

    def test_description_with_no_values_returns_empty_string(self):
        assert self.describe() == ""

    def test_description_relabels_registration_status(self):
        self.values = {A.DECISION_REGISTRATION_STATUS: "Registered"}
        result = self.describe()
        assert "Registration Status" in result and "Registered" in result
        assert "Raw Status Node Name" not in result

    def test_description_uses_the_node_name_for_everything_else(self):
        self.values = {A.NAME: "Cedar Bluff"}
        result = self.describe()
        assert "Site Name" in result and "Cedar Bluff" in result

    def test_description_appends_the_typology_block(self):
        self.typologies = (["Habitation"], ["Midden"])
        result = self.describe()
        assert "Site Class" in result and "Habitation" in result
        assert "Descriptor" in result and "Midden" in result

    def test_empty_typologies_render_nothing(self):
        # The base's _format_value wraps even an empty value in its label
        # template, so an unguarded call would emit a stray empty label.
        self.typologies = ([], [])
        assert self.describe() == ""

    def test_first_only_returns_first_value_and_stops(self):
        self.values = {A.DECISION_REGISTRATION_STATUS: "Registered", A.NAME: "Cedar"}
        result = self.describe(first_only=True, show_name=False)
        assert result == "Registered"
        assert self.reads == [A.DECISION_REGISTRATION_STATUS]

    def test_first_only_relabels_registration_status_too(self):
        """Deliberate: first_only used to skip the relabel because it formatted
        in a separate loop. The two paths label identically now."""
        self.values = {A.DECISION_REGISTRATION_STATUS: "Registered"}
        result = self.describe(first_only=True, show_name=True)
        assert "Registration Status" in result
        assert "Raw Status Node Name" not in result

    def test_map_popup_walks_the_popup_aliases(self):
        self.describe(descriptor="map_popup")
        assert self.reads == BCAPSiteDescriptors._popup_node_aliases

    def test_typology_block_has_no_alias_to_walk(self):
        """It is derived from tiles, so it is not in the alias lists and cannot
        be reached by walking them."""
        assert "typologies" not in BCAPSiteDescriptors.get_all_nodes()
        self.typologies = (["Habitation"], [])
        assert "Habitation" in self.describe(descriptor="map_popup")


class TestGetSiteName(SiteDescriptorTestCase):
    def setUp(self):
        super().setUp()
        self.datatype = BCAPSiteDescriptors._datatypes[A.BORDEN_NUMBER]
        models = patch("bcap.functions.bcap_site_descriptors.models")
        self.mock_models = models.start()
        self.addCleanup(models.stop)

    def _tile(self, tile):
        self.mock_models.TileModel.objects.filter.return_value.first.return_value = tile

    def test_returns_borden_number_display_value(self):
        tile = MagicMock()
        self._tile(tile)
        self.datatype.get_display_value.return_value = "DjRi-123"

        assert BCAPSiteDescriptors._get_site_name(MagicMock()) == "DjRi-123"
        self.datatype.get_display_value.assert_called_once_with(
            tile, BCAPSiteDescriptors._nodes[A.BORDEN_NUMBER]
        )

    def test_falls_back_to_placeholder_when_no_tile(self):
        self._tile(None)
        assert BCAPSiteDescriptors._get_site_name(MagicMock()) == "(No official name)"

    def test_falls_back_to_placeholder_when_display_value_empty(self):
        self._tile(MagicMock())
        self.datatype.get_display_value.return_value = ""
        assert BCAPSiteDescriptors._get_site_name(MagicMock()) == "(No official name)"


class TestGetAllNodes(TestCase):
    def test_includes_significant_event_nodes(self):
        all_nodes = BCAPSiteDescriptors.get_all_nodes()
        assert A.BORDEN_NUMBER in all_nodes
        assert A.TYPOLOGY_CLASS in all_nodes
        assert A.DECISION_REGISTRATION_STATUS in all_nodes


class TestFirstOnlyCoversTheTypologyBlock(SiteDescriptorTestCase):
    """first_only used to stop at the node aliases and then render both
    typology entries anyway, so a site with no node values got two."""

    def test_typology_block_stops_after_site_class(self):
        self.typologies = (["Habitation"], ["Midden"])
        result = self.describe(first_only=True, show_name=True)
        assert "Site Class" in result and "Habitation" in result
        assert "Descriptor" not in result and "Midden" not in result

    def test_falls_through_to_descriptor_when_no_site_class(self):
        self.typologies = ([], ["Midden"])
        result = self.describe(first_only=True, show_name=True)
        assert "Descriptor" in result and "Midden" in result

    def test_a_node_value_still_wins_over_the_typology_block(self):
        self.values = {A.NAME: "Cedar Bluff"}
        self.typologies = (["Habitation"], ["Midden"])
        result = self.describe(first_only=True, show_name=True)
        assert "Cedar Bluff" in result
        assert "Site Class" not in result
