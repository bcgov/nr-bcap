"""
Unit tests for BCAPSiteDescriptors.

Django/Arches is already configured by the test runner; individual ORM calls
are mocked with @patch so no database access is required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from django.test import TestCase

# DataTypeFactory() is evaluated at class-body level when the module is first
# imported. In CI the DB tables don't exist at collection time, so we mock it
# for the duration of the import to prevent a premature DB query.
with patch("arches.app.datatypes.datatypes.DataTypeFactory"):
    from bcap.functions.bcap_site_descriptors import BCAPSiteDescriptors

from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases as A


def _make_node(alias, name, datatype="string", nodegroup_id="ng-1", nodeid="node-1"):
    node = MagicMock()
    node.alias = alias
    node.name = name
    node.datatype = datatype
    node.nodegroup_id = nodegroup_id
    node.nodeid = nodeid
    return node


def _reset_class_state():
    """Reset class-level caches between tests."""
    BCAPSiteDescriptors._initialized = False
    BCAPSiteDescriptors._nodes = {}
    BCAPSiteDescriptors._datatypes = {}
    BCAPSiteDescriptors._html_nodes = []


class TestDescriptorDispatch(TestCase):
    """The base dispatches on the descriptor argument, not config["type"]."""

    def setUp(self):
        _reset_class_state()
        BCAPSiteDescriptors._initialized = True  # skip initialize()
        self.fn = BCAPSiteDescriptors()

    def tearDown(self):
        _reset_class_state()

    def test_name_descriptor_delegates_to_get_site_name(self):
        resource = MagicMock()
        with patch.object(
            BCAPSiteDescriptors, "_get_site_name", return_value="DjRi-123"
        ) as mock_name:
            result = self.fn.get_primary_descriptor_from_nodes(
                resource, config={}, descriptor="name"
            )
        assert result == "DjRi-123"
        assert mock_name.call_args.args[0] is resource

    def test_description_with_no_values_returns_empty_string(self):
        with patch.object(
            BCAPSiteDescriptors, "_get_typologies", return_value=([], [])
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": False, "show_name": True},
                descriptor="description",
            )
        assert result == ""

    def test_description_labels_registration_status_and_typologies(self):
        BCAPSiteDescriptors._nodes = {
            A.DECISION_REGISTRATION_STATUS: _make_node(
                A.DECISION_REGISTRATION_STATUS, "Raw Status Node Name"
            ),
            A.NAME: _make_node(A.NAME, "Site Name"),
        }
        values = {
            A.DECISION_REGISTRATION_STATUS: "Registered",
            A.NAME: "Cedar Bluff",
        }

        with (
            patch.object(
                BCAPSiteDescriptors,
                "_get_value_from_node",
                side_effect=lambda node_alias, *a, **kw: values.get(node_alias),
            ),
            patch.object(
                BCAPSiteDescriptors,
                "_get_typologies",
                return_value=(["Habitation"], ["Midden"]),
            ),
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": False, "show_name": True},
                descriptor="description",
            )

        assert "Registration Status" in result
        assert "Raw Status Node Name" not in result
        assert "Registered" in result
        assert "Site Name" in result and "Cedar Bluff" in result
        assert "Site Class" in result and "Habitation" in result
        assert "Descriptor" in result and "Midden" in result

    def test_first_only_returns_first_value_and_stops(self):
        BCAPSiteDescriptors._nodes = {
            A.DECISION_REGISTRATION_STATUS: _make_node(
                A.DECISION_REGISTRATION_STATUS, "Status"
            ),
        }
        call_log: list[str] = []

        def side_effect(node_alias, *args, **kwargs):
            call_log.append(node_alias)
            return "Registered"

        with patch.object(
            BCAPSiteDescriptors, "_get_value_from_node", side_effect=side_effect
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": True, "show_name": False},
                descriptor="description",
            )

        assert result == "Registered"
        assert call_log == [A.DECISION_REGISTRATION_STATUS]

    def test_map_popup_uses_popup_aliases(self):
        with patch.object(
            BCAPSiteDescriptors, "_get_typologies", return_value=([], [])
        ) as mock_typologies:
            self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"first_only": False, "show_name": True},
                descriptor="map_popup",
            )
        # "typologies" is in _popup_node_aliases, so reaching it proves the
        # popup list was walked rather than the card list being reused blindly.
        mock_typologies.assert_called_once()


class TestGetSiteName(TestCase):
    def setUp(self):
        _reset_class_state()
        self.datatype = MagicMock()
        self.node = _make_node(A.BORDEN_NUMBER, "Borden Number")
        BCAPSiteDescriptors._nodes = {A.BORDEN_NUMBER: self.node}
        BCAPSiteDescriptors._datatypes = {A.BORDEN_NUMBER: self.datatype}

    def tearDown(self):
        _reset_class_state()

    @patch("bcap.functions.bcap_site_descriptors.models")
    def test_returns_borden_number_display_value(self, mock_models):
        tile = MagicMock()
        mock_models.TileModel.objects.filter.return_value.first.return_value = tile
        self.datatype.get_display_value.return_value = "DjRi-123"

        assert BCAPSiteDescriptors._get_site_name(MagicMock()) == "DjRi-123"
        self.datatype.get_display_value.assert_called_once_with(tile, self.node)

    @patch("bcap.functions.bcap_site_descriptors.models")
    def test_falls_back_to_placeholder_when_no_tile(self, mock_models):
        mock_models.TileModel.objects.filter.return_value.first.return_value = None

        assert BCAPSiteDescriptors._get_site_name(MagicMock()) == "(No official name)"

    @patch("bcap.functions.bcap_site_descriptors.models")
    def test_falls_back_to_placeholder_when_display_value_empty(self, mock_models):
        mock_models.TileModel.objects.filter.return_value.first.return_value = (
            MagicMock()
        )
        self.datatype.get_display_value.return_value = ""

        assert BCAPSiteDescriptors._get_site_name(MagicMock()) == "(No official name)"


class TestGetAllNodes(TestCase):
    def test_includes_significant_event_nodes(self):
        all_nodes = BCAPSiteDescriptors.get_all_nodes()
        assert A.BORDEN_NUMBER in all_nodes
        assert A.TYPOLOGY_CLASS in all_nodes
        assert A.DECISION_REGISTRATION_STATUS in all_nodes
