"""
Unit tests for ProcessRequirementDescriptors.

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
    from bcap.functions.process_requirement_descriptors import (
        ProcessRequirementDescriptors,
    )

from bcap.util.aliases.process_requirement import ProcessRequirementAliases as A


def _make_node(alias, name, datatype="string", nodegroup_id="ng-1", nodeid="node-1"):
    node = MagicMock()
    node.alias = alias
    node.name = name
    node.datatype = datatype
    node.nodegroup_id = nodegroup_id
    node.nodeid = nodeid
    return node


def _make_tile(data=None):
    tile = MagicMock()
    tile.data = data if data is not None else {}
    return tile


def _reset_class_state():
    """Reset class-level caches between tests."""
    ProcessRequirementDescriptors._initialized = False
    ProcessRequirementDescriptors._nodes = {}
    ProcessRequirementDescriptors._datatypes = {}


class TestFormatValue(TestCase):
    def _call(self, name, value, show_name, first_only=False):
        config = {"show_name": show_name, "first_only": first_only}
        return ProcessRequirementDescriptors._format_value(name, value, config)

    def test_string_show_name_false_returns_raw_value(self):
        assert self._call("Label", "Hello", show_name=False) == "Hello"

    def test_string_show_name_true_returns_html_with_name_and_value(self):
        result = self._call("Label", "Value", show_name=True)
        assert "bc-popup-label" in result
        assert "Label" in result
        assert "Value" in result

    def test_empty_string_returns_empty(self):
        assert self._call("Label", "", show_name=False) == ""

    def test_none_returns_empty(self):
        assert self._call("Label", None, show_name=False) == ""

    def test_list_sorts_and_joins_values(self):
        assert self._call("L", ["C", "A", "B"], show_name=False) == "A, B, C"

    def test_list_removes_empty_strings(self):
        assert self._call("L", ["B", "", "A"], show_name=False) == "A, B"

    def test_list_deduplicates(self):
        assert self._call("L", ["A", "A", "B"], show_name=False) == "A, B"

    def test_list_all_empty_returns_empty(self):
        assert self._call("L", ["", ""], show_name=False) == ""


class TestGetValueFromNode(TestCase):
    def setUp(self):
        _reset_class_state()

    def tearDown(self):
        _reset_class_state()

    def test_returns_none_when_alias_not_registered(self):
        result = ProcessRequirementDescriptors._get_value_from_node("unknown_alias")
        assert result is None

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_returns_none_when_no_tiles_exist(self, mock_models):
        node = _make_node(A.REQUIREMENT_NAME, "Name")
        ProcessRequirementDescriptors._nodes[A.REQUIREMENT_NAME] = node
        ProcessRequirementDescriptors._datatypes[A.REQUIREMENT_NAME] = MagicMock()
        mock_models.TileModel.objects.filter.return_value.filter.return_value.all.return_value = (
            []
        )

        result = ProcessRequirementDescriptors._get_value_from_node(
            A.REQUIREMENT_NAME, resourceinstanceid="res-1"
        )
        assert result is None

    def test_returns_single_value_for_one_tile(self):
        node = _make_node(A.REQUIREMENT_NAME, "Name")
        datatype = MagicMock()
        datatype.get_display_value.return_value = "My Requirement"
        ProcessRequirementDescriptors._nodes[A.REQUIREMENT_NAME] = node
        ProcessRequirementDescriptors._datatypes[A.REQUIREMENT_NAME] = datatype

        tile = _make_tile()
        result = ProcessRequirementDescriptors._get_value_from_node(
            A.REQUIREMENT_NAME, data_tile=tile
        )

        assert result == "My Requirement"
        datatype.get_display_value.assert_called_once_with(tile, node)

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_returns_list_for_multiple_tiles_from_db(self, mock_models):
        node = _make_node(A.REQUIREMENT_STATUS, "Status")
        datatype = MagicMock()
        datatype.get_display_value.side_effect = ["Active", "Closed"]
        ProcessRequirementDescriptors._nodes[A.REQUIREMENT_STATUS] = node
        ProcessRequirementDescriptors._datatypes[A.REQUIREMENT_STATUS] = datatype

        tile1, tile2 = _make_tile(), _make_tile()
        mock_models.TileModel.objects.filter.return_value.filter.return_value.all.return_value = [
            tile1,
            tile2,
        ]
        result = ProcessRequirementDescriptors._get_value_from_node(
            A.REQUIREMENT_STATUS, resourceinstanceid="res-1"
        )
        assert result == ["Active", "Closed"]

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_uses_data_tile_and_skips_db_query(self, mock_models):
        node = _make_node(A.REQUIREMENT_NAME, "Name")
        datatype = MagicMock()
        datatype.get_display_value.return_value = "From tile"
        ProcessRequirementDescriptors._nodes[A.REQUIREMENT_NAME] = node
        ProcessRequirementDescriptors._datatypes[A.REQUIREMENT_NAME] = datatype

        ProcessRequirementDescriptors._get_value_from_node(
            A.REQUIREMENT_NAME, data_tile=_make_tile()
        )
        mock_models.TileModel.objects.filter.assert_not_called()


class TestGetPrimaryDescriptorFromNodes(TestCase):
    def setUp(self):
        _reset_class_state()
        ProcessRequirementDescriptors._initialized = True  # skip initialize()
        self.fn = ProcessRequirementDescriptors()

    def tearDown(self):
        _reset_class_state()

    def test_name_config_delegates_to_get_process_requirement_name(self):
        resource = MagicMock()
        with patch.object(
            self.fn, "_get_process_requirement_name", return_value="Req Name"
        ) as mock_name:
            result = self.fn.get_primary_descriptor_from_nodes(
                resource, config={"type": "name"}
            )
        mock_name.assert_called_once_with(resource)
        assert result == "Req Name"

    def test_description_with_no_matching_values_returns_empty_string(self):
        result = self.fn.get_primary_descriptor_from_nodes(
            MagicMock(),
            config={"type": "description", "first_only": False, "show_name": True},
        )
        assert result == ""

    def test_description_concatenates_all_non_null_values(self):
        ProcessRequirementDescriptors._nodes = {
            A.REQUIREMENT_IDENTIFICATION: _make_node(
                A.REQUIREMENT_IDENTIFICATION, "ID"
            ),
            A.REQUIREMENT_STATUS: _make_node(A.REQUIREMENT_STATUS, "Status"),
            A.REQUIREMENT_PROCESS_START_DATE: _make_node(
                A.REQUIREMENT_PROCESS_START_DATE, "Start"
            ),
        }
        ProcessRequirementDescriptors._datatypes = {
            k: MagicMock() for k in ProcessRequirementDescriptors._nodes
        }
        values = {
            A.REQUIREMENT_IDENTIFICATION: "ID Value",
            A.REQUIREMENT_STATUS: "Active",
            A.REQUIREMENT_PROCESS_START_DATE: None,
        }

        with patch.object(
            ProcessRequirementDescriptors,
            "_get_value_from_node",
            side_effect=lambda alias, resource: values.get(alias),
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"type": "description", "first_only": False, "show_name": False},
            )

        assert "ID Value" in result
        assert "Active" in result

    def test_first_only_returns_on_first_truthy_value_and_stops(self):
        ProcessRequirementDescriptors._nodes = {
            A.REQUIREMENT_IDENTIFICATION: _make_node(
                A.REQUIREMENT_IDENTIFICATION, "ID"
            ),
            A.REQUIREMENT_STATUS: _make_node(A.REQUIREMENT_STATUS, "Status"),
        }
        ProcessRequirementDescriptors._datatypes = {
            k: MagicMock() for k in ProcessRequirementDescriptors._nodes
        }

        call_log: list[str] = []

        def side_effect(alias, resource):
            call_log.append(alias)
            return (
                "First Value"
                if alias == A.REQUIREMENT_IDENTIFICATION
                else "Should not reach"
            )

        with patch.object(
            ProcessRequirementDescriptors,
            "_get_value_from_node",
            side_effect=side_effect,
        ):
            result = self.fn.get_primary_descriptor_from_nodes(
                MagicMock(),
                config={"type": "description", "first_only": True, "show_name": False},
            )

        assert result == "First Value"
        assert call_log == [A.REQUIREMENT_IDENTIFICATION]

    def test_map_popup_uses_popup_nodes_which_are_empty(self):
        """_popup_nodes is [] so map_popup always returns an empty string."""
        result = self.fn.get_primary_descriptor_from_nodes(
            MagicMock(),
            config={"type": "map_popup", "first_only": False, "show_name": True},
        )
        assert result == ""


class TestGetProcessRequirementName(TestCase):
    NAME_NODE_ID = "node-name"
    TMPL_NODE_ID = "node-tmpl"

    def setUp(self):
        _reset_class_state()
        ProcessRequirementDescriptors._initialized = True
        self._setup_nodes()
        self.fn = ProcessRequirementDescriptors()

    def tearDown(self):
        _reset_class_state()

    def _setup_nodes(self):
        name_node = _make_node(
            A.REQUIREMENT_NAME,
            "Name",
            nodeid=self.NAME_NODE_ID,
            nodegroup_id="ng-name",
        )
        tmpl_node = _make_node(
            A.IS_TEMPLATE_REQUIREMENT,
            "Is Template",
            nodeid=self.TMPL_NODE_ID,
            nodegroup_id="ng-tmpl",
        )
        self.name_datatype = MagicMock()
        ProcessRequirementDescriptors._nodes = {
            A.REQUIREMENT_NAME: name_node,
            A.IS_TEMPLATE_REQUIREMENT: tmpl_node,
        }
        ProcessRequirementDescriptors._datatypes = {
            A.REQUIREMENT_NAME: self.name_datatype,
            A.IS_TEMPLATE_REQUIREMENT: MagicMock(),
        }

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_no_name_tile_no_permit_returns_empty_name_value(self, mock_models):
        mock_models.TileModel.objects.filter.return_value.first.return_value = None
        mock_models.ResourceXResource.objects.filter.return_value.first.return_value = (
            None
        )

        result = self.fn._get_process_requirement_name(MagicMock())

        # No name and no permit: nothing to show, fall back to the placeholder.
        assert result == "(Unknown)"

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_template_resource_appends_template_suffix(self, mock_models):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        name_tile = _make_tile()
        tmpl_tile = _make_tile(data={self.TMPL_NODE_ID: True})
        mock_models.TileModel.objects.filter.return_value.first.side_effect = [
            name_tile,
            tmpl_tile,
        ]

        result = self.fn._get_process_requirement_name(MagicMock())
        assert result == "My Requirement (Template)"

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_non_template_with_permit_prefixes_permit_name(self, mock_models):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        name_tile = _make_tile()
        tmpl_tile = _make_tile(data={self.TMPL_NODE_ID: False})
        permit = MagicMock()
        permit.from_resource.descriptors = {"en": {"name": "Permit ABC"}}
        # name tile, template tile, then the module-id lookup finds no
        # process_module tile referencing this requirement (no module prefix).
        mock_models.TileModel.objects.filter.return_value.first.side_effect = [
            name_tile,
            tmpl_tile,
            None,
        ]
        mock_models.ResourceXResource.objects.filter.return_value.first.return_value = (
            permit
        )

        result = self.fn._get_process_requirement_name(MagicMock())
        assert result == "Permit ABC - My Requirement"

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_non_template_with_permit_and_module_prefixes_both(self, mock_models):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        name_tile = _make_tile()
        tmpl_tile = _make_tile(data={self.TMPL_NODE_ID: False})
        permit = MagicMock()
        permit.from_resource.descriptors = {"en": {"name": "APP-107"}}
        # The module-id lookup: a process_module child tile references this
        # requirement; its parent module tile carries the module id.
        child_tile = MagicMock(parenttile_id="parent-1")
        parent_tile = MagicMock()
        parent_tile.data.get.return_value = "PERMIT-APPLICATION-1"
        mock_models.TileModel.objects.filter.return_value.first.side_effect = [
            name_tile,
            tmpl_tile,
            child_tile,
            parent_tile,
        ]
        mock_models.ResourceXResource.objects.filter.return_value.first.return_value = (
            permit
        )

        result = self.fn._get_process_requirement_name(MagicMock())
        assert result == "APP-107 - PERMIT-APPLICATION-1 - My Requirement"

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_non_template_no_permit_shows_name_only(self, mock_models):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        name_tile = _make_tile()
        tmpl_tile = _make_tile(data={self.TMPL_NODE_ID: False})
        # name tile, template tile, then no process_module tile for the module id.
        mock_models.TileModel.objects.filter.return_value.first.side_effect = [
            name_tile,
            tmpl_tile,
            None,
        ]
        # A grouping parent has no permit reference, so no permit prefix.
        mock_models.ResourceXResource.objects.filter.return_value.first.return_value = (
            None
        )

        result = self.fn._get_process_requirement_name(MagicMock())
        assert result == "My Requirement"


class TestInitialize(TestCase):
    def setUp(self):
        _reset_class_state()

    def tearDown(self):
        _reset_class_state()

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_sets_initialized_flag(self, mock_models):
        mock_models.Node.objects.filter.return_value.first.return_value = None
        ProcessRequirementDescriptors().initialize()
        assert ProcessRequirementDescriptors._initialized is True

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_populates_nodes_and_datatypes_for_found_nodes(self, mock_models):
        found_node = _make_node(A.REQUIREMENT_NAME, "Name", datatype="string")
        datatype_instance = MagicMock()
        mock_factory = MagicMock()
        mock_factory.get_instance.return_value = datatype_instance

        def filter_side_effect(**kwargs):
            qs = MagicMock()
            qs.first.return_value = (
                found_node if kwargs.get("alias") == A.REQUIREMENT_NAME else None
            )
            return qs

        mock_models.Node.objects.filter.side_effect = filter_side_effect
        ProcessRequirementDescriptors._datatype_factory = mock_factory
        ProcessRequirementDescriptors().initialize()

        assert A.REQUIREMENT_NAME in ProcessRequirementDescriptors._nodes
        assert A.REQUIREMENT_NAME in ProcessRequirementDescriptors._datatypes
        assert A.REQUIREMENT_STATUS not in ProcessRequirementDescriptors._nodes

    @patch("bcap.functions.process_requirement_descriptors.models")
    def test_initialize_not_called_when_already_initialized(self, mock_models):
        ProcessRequirementDescriptors._initialized = True
        fn = ProcessRequirementDescriptors()

        with patch.object(fn, "_get_process_requirement_name", return_value="x"):
            fn.get_primary_descriptor_from_nodes(MagicMock(), config={"type": "name"})

        mock_models.Node.objects.filter.assert_not_called()
