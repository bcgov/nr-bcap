"""
Unit tests for ProcessRequirementDescriptors.
"""

from __future__ import annotations

from collections import defaultdict
from unittest.mock import MagicMock, patch

from bcap.functions.process_requirement_descriptors import (
    ProcessRequirementDescriptors,
)

from bcap.util.aliases.process_requirement import ProcessRequirementAliases as A
from tests.functions.descriptor_helpers import DescriptorTestCase, make_node, make_tile


class ProcessRequirementTestCase(DescriptorTestCase):
    descriptor_class = ProcessRequirementDescriptors
    node_names = {
        A.REQUIREMENT_IDENTIFICATION: "ID",
        A.REQUIREMENT_STATUS: "Status",
        A.REQUIREMENT_PROCESS_START_DATE: "Start",
    }


class TestGetPrimaryDescriptorFromNodes(ProcessRequirementTestCase):
    def setUp(self):
        super().setUp()
        # The descriptor loads the resource's tiles once up front; the stubbed
        # _get_value_from_node drives the logic instead.
        self.stub("_tiles_by_nodegroup", return_value=defaultdict(list))

    def test_name_config_delegates_to_get_process_requirement_name(self):
        resource = MagicMock()
        mock_name = self.stub("_get_process_requirement_name", return_value="Req Name")
        result = self.fn.get_primary_descriptor_from_nodes(
            resource, config={}, descriptor="name"
        )
        assert mock_name.call_args.args[0] is resource
        assert result == "Req Name"

    def test_description_with_no_matching_values_returns_empty_string(self):
        assert self.describe() == ""

    def test_description_concatenates_all_non_null_values(self):
        self.values = {
            A.REQUIREMENT_IDENTIFICATION: "ID Value",
            A.REQUIREMENT_STATUS: "Active",
            A.REQUIREMENT_PROCESS_START_DATE: None,
        }
        result = self.describe(show_name=False)
        assert "ID Value" in result
        assert "Active" in result

    def test_first_only_returns_on_first_truthy_value_and_stops(self):
        self.values = {
            A.REQUIREMENT_IDENTIFICATION: "First Value",
            A.REQUIREMENT_STATUS: "Should not reach",
        }
        result = self.describe(first_only=True, show_name=False)
        assert result == "First Value"
        assert self.reads == [A.REQUIREMENT_IDENTIFICATION]

    def test_map_popup_uses_popup_nodes_which_are_empty(self):
        """_popup_node_aliases is [] so map_popup always returns an empty string."""
        assert self.describe(descriptor="map_popup") == ""
        assert self.reads == []


class TestGetProcessRequirementName(ProcessRequirementTestCase):
    NAME_NODE_ID = "node-name"
    TMPL_NODE_ID = "node-tmpl"
    node_names = {
        A.REQUIREMENT_NAME: "Name",
        A.IS_TEMPLATE_REQUIREMENT: "Is Template",
    }

    def setUp(self):
        super().setUp()
        nodes = ProcessRequirementDescriptors._nodes
        nodes[A.REQUIREMENT_NAME] = make_node(
            "Name", nodegroup_id="ng-name", nodeid=self.NAME_NODE_ID
        )
        nodes[A.IS_TEMPLATE_REQUIREMENT] = make_node(
            "Is Template", nodegroup_id="ng-tmpl", nodeid=self.TMPL_NODE_ID
        )
        self.name_datatype = ProcessRequirementDescriptors._datatypes[
            A.REQUIREMENT_NAME
        ]
        models = patch("bcap.functions.process_requirement_descriptors.models")
        self.mock_models = models.start()
        self.addCleanup(models.stop)

    def _permit_lookup(self, permit):
        """What the permit-reference query returns; it select_relateds the
        permit so the descriptor reads its name without a second query."""
        objects = self.mock_models.ResourceXResource.objects
        objects.filter.return_value.select_related.return_value.first.return_value = (
            permit
        )

    def _module_child_tile(self, child):
        """What the module-id lookup returns: the process_module child tile,
        with its parent already joined."""
        objects = self.mock_models.TileModel.objects
        objects.filter.return_value.select_related.return_value.first.return_value = (
            child
        )

    @staticmethod
    def _tiles(name_tile=None, template_tile=None):
        """The resource's tiles by nodegroup, as the caller now hands them over."""
        return defaultdict(
            list,
            {
                "ng-name": [name_tile] if name_tile else [],
                "ng-tmpl": [template_tile] if template_tile else [],
            },
        )

    def _name(self, name_tile=None, template_tile=None):
        return self.fn._get_process_requirement_name(
            MagicMock(), self._tiles(name_tile, template_tile)
        )

    def test_no_name_tile_no_permit_returns_empty_name_value(self):
        self._permit_lookup(None)
        # No name and no permit: nothing to show, fall back to the placeholder.
        assert self._name() == "(Unknown)"

    def test_template_resource_appends_template_suffix(self):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        template = make_tile(data={self.TMPL_NODE_ID: True})
        assert self._name(make_tile(), template) == "My Requirement (Template)"

    def test_non_template_with_permit_prefixes_permit_name(self):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        permit = MagicMock()
        permit.from_resource.descriptors = {"en": {"name": "Permit ABC"}}
        # The module-id lookup finds no process_module tile referencing this
        # requirement, so there is no module prefix.
        self._module_child_tile(None)
        self._permit_lookup(permit)

        template = make_tile(data={self.TMPL_NODE_ID: False})
        assert self._name(make_tile(), template) == "Permit ABC - My Requirement"

    def test_non_template_with_permit_and_module_prefixes_both(self):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        permit = MagicMock()
        permit.from_resource.descriptors = {"en": {"name": "APP-107"}}
        # A process_module child tile references this requirement; its parent
        # module tile carries the module id.
        parent_tile = MagicMock()
        parent_tile.data.get.return_value = "PERMIT-APPLICATION-1"
        self._module_child_tile(MagicMock(parenttile=parent_tile))
        self._permit_lookup(permit)

        template = make_tile(data={self.TMPL_NODE_ID: False})
        assert (
            self._name(make_tile(), template)
            == "APP-107 - PERMIT-APPLICATION-1 - My Requirement"
        )

    def test_non_template_no_permit_shows_name_only(self):
        self.name_datatype.get_display_value.return_value = "My Requirement"
        # A grouping parent has no permit reference, so no permit prefix.
        self._permit_lookup(None)
        template = make_tile(data={self.TMPL_NODE_ID: False})
        assert self._name(make_tile(), template) == "My Requirement"
