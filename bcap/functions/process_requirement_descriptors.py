from collections import defaultdict

from arches.app.functions.primary_descriptors import AbstractPrimaryDescriptorsFunction
from arches.app.models import models
from arches.app.datatypes.datatypes import DataTypeFactory
from bcap.util.aliases.permit_application import PermitApplicationAliases as pa
from bcap.util.aliases.process_requirement import ProcessRequirementAliases as aliases
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.graph import node_id

details = {
    "functionid": "60000000-0000-0000-0000-000000001006",
    "name": "BCAP Process Requirement Descriptors",
    "type": "primarydescriptors",
    "modulename": "process_requirement_descriptors.py",
    "description": "Function that provides the primary descriptors for Process Requirements",
    "defaultconfig": {
        "module": "bcap.functions.process_requirement_descriptors",
        "class_name": "ProcessRequirementDescriptors",
        "descriptor_types": {
            "name": {
                "type": "name",
                "node_ids": [],
                "first_only": True,
                "show_name": False,
            },
            "description": {
                "type": "description",
                "node_ids": [],
                "first_only": False,
                "delimiter": "<br>",
                "show_name": True,
            },
            "map_popup": {
                "type": "map_popup",
                "node_ids": [],
                "first_only": False,
                "delimiter": "<br>",
                "show_name": True,
            },
        },
        "triggering_nodegroups": [],
    },
    "classname": "ProcessRequirementDescriptors",
    "component": "views/components/functions/process_requirement-descriptors",
}


class ProcessRequirementDescriptors(AbstractPrimaryDescriptorsFunction):
    _datatype_factory = None
    # For Name part of descriptor
    graph_slug = "process_requirement"

    _empty_name_value = "(Unknown)"
    _nodes = {}
    _datatypes = {}

    _initialized = False

    # @todo Change these to aliases
    _name_nodes = [aliases.REQUIREMENT_NAME, aliases.IS_TEMPLATE_REQUIREMENT]
    # These don't have a geometry
    _popup_nodes = []
    _card_nodes = [
        aliases.REQUIREMENT_IDENTIFICATION,
        aliases.REQUIREMENT_STATUS,
        aliases.REQUIREMENT_PROCESS_START_DATE,
    ]

    # Initializes the static nodes and datatypes data
    def initialize(self):
        ProcessRequirementDescriptors._datatype_factory = DataTypeFactory()
        for alias in (
            ProcessRequirementDescriptors._name_nodes
            + ProcessRequirementDescriptors._popup_nodes
            + ProcessRequirementDescriptors._card_nodes
        ):
            node = models.Node.objects.filter(
                alias=alias,
                graph__slug=ProcessRequirementDescriptors.graph_slug,
                source_identifier__isnull=True,
            ).first()
            if node:
                ProcessRequirementDescriptors._nodes[alias] = node
                ProcessRequirementDescriptors._datatypes[alias] = (
                    ProcessRequirementDescriptors._datatype_factory.get_instance(
                        node.datatype
                    )
                )

        ProcessRequirementDescriptors._initialized = True

    def get_primary_descriptor_from_nodes(
        self, resource, config, context=None, descriptor=None
    ):
        if not ProcessRequirementDescriptors._initialized:
            self.initialize()

        return_value = ""
        display_values = {}

        try:
            if config["type"] == "name":
                return self._get_process_requirement_name(
                    resource, self._tiles_by_nodegroup(resource)
                )

            _description_order = (
                self._popup_nodes if config["type"] == "map_popup" else self._card_nodes
            )
            if not _description_order:
                return return_value

            tiles = self._tiles_by_nodegroup(resource)
            nodes = ProcessRequirementDescriptors._nodes
            for node_alias in _description_order:
                value = ProcessRequirementDescriptors._get_value_from_node(
                    node_alias, resource, tiles_by_nodegroup=tiles
                )
                if value:
                    if config["first_only"]:
                        return ProcessRequirementDescriptors._format_value(
                            nodes[node_alias].name, value, config
                        )
                    display_values[node_alias] = value

            for alias in _description_order:
                if alias in display_values:
                    return_value += ProcessRequirementDescriptors._format_value(
                        nodes[alias].name, display_values[alias], config
                    )

            return return_value

        except ValueError as e:
            print(e, "invalid nodegroupid participating in descriptor function.")

    @staticmethod
    def _tiles_by_nodegroup(resource):
        """The resource's tiles grouped by nodegroup id. A descriptor reads
        several nodegroups per call, which was a query apiece."""
        grouped = defaultdict(list)
        for tile in models.TileModel.objects.filter(
            resourceinstance_id=resource.resourceinstanceid
        ):
            grouped[str(tile.nodegroup_id)].append(tile)
        return grouped

    @staticmethod
    def _get_value_from_node(
        node_alias, resourceinstanceid=None, data_tile=None, tiles_by_nodegroup=None
    ):
        """
        get the display value from the resource tile(s) for the node with the given name

        Keyword Arguments

        node_alias -- node alias of the data to extract
        resourceinstanceid -- id of resource instance used to fetch the tile(s) if data_tile not specified
        data_tile -- if specified, the tile to extract the value from
        """
        if node_alias not in ProcessRequirementDescriptors._nodes:
            return None

        display_values = []
        datatype = ProcessRequirementDescriptors._datatypes[node_alias]

        nodegroup_id = str(
            ProcessRequirementDescriptors._nodes[node_alias].nodegroup_id
        )
        if data_tile:
            tiles = [data_tile]
        elif tiles_by_nodegroup is not None:
            tiles = tiles_by_nodegroup[nodegroup_id]
        else:
            tiles = models.TileModel.objects.filter(
                nodegroup_id=nodegroup_id, resourceinstance_id=resourceinstanceid
            )

        for tile in tiles:
            if tile:
                display_values.append(
                    datatype.get_display_value(
                        tile, ProcessRequirementDescriptors._nodes[node_alias]
                    )
                )

        return (
            None
            if len(display_values) == 0
            else (display_values[0] if len(display_values) == 1 else display_values)
        )

    @staticmethod
    def _format_value(name, value, config):
        if type(value) is list:
            value = set(value)
            if "" in value:
                value.remove("")
            value = ", ".join(sorted(value))

        if not value:
            return ""
        elif config["show_name"]:
            return (
                "<div class='bc-popup-entry'><div class='bc-popup-label'>%s</div><div class='bc-popup-value'>%s</div></div>"
                % (name, value)
            )
        return value

    def _get_process_requirement_name(self, resource, tiles_by_nodegroup):
        name_datatype = ProcessRequirementDescriptors._datatypes[
            aliases.REQUIREMENT_NAME
        ]
        display_value = ""

        def first_tile(alias):
            nodegroup_id = str(ProcessRequirementDescriptors._nodes[alias].nodegroup_id)
            return next(iter(tiles_by_nodegroup[nodegroup_id]), None)

        name_tile = first_tile(aliases.REQUIREMENT_NAME)
        is_template_tile = first_tile(aliases.IS_TEMPLATE_REQUIREMENT)

        if name_tile:
            display_value += "%s" % name_datatype.get_display_value(
                name_tile,
                ProcessRequirementDescriptors._nodes[aliases.REQUIREMENT_NAME],
            )

        if (
            is_template_tile
            and is_template_tile.data[
                str(
                    ProcessRequirementDescriptors._nodes[
                        aliases.IS_TEMPLATE_REQUIREMENT
                    ].nodeid
                )
            ]
        ):
            display_value += " (Template)"
        else:
            # The permit that references this requirement -- not a child that
            # references it as its grouping parent. A grouping parent has no
            # permit reference, so it shows just its name.
            permit = (
                models.ResourceXResource.objects.filter(
                    to_resource=resource,
                    from_resource__graph__slug="permit_application",
                )
                .select_related("from_resource")
                .first()
            )
            # Only an attached requirement has an app/module prefix; skip the
            # lookup entirely for a cloned or grouping-parent one (no permit).
            if permit is not None:
                descriptors = permit.from_resource.descriptors
                app_id = (descriptors or {}).get("en", {}).get("name")
                module_id = self._module_id_for_requirement(
                    resource.resourceinstanceid, permit.from_resource_id
                )
                # app id - module id - name, dropping whichever prefix is missing
                # so a grouping parent (no module) still reads cleanly.
                prefix = " - ".join(part for part in (app_id, module_id) if part)
                if prefix:
                    display_value = f"{prefix} - {display_value}"

        return display_value if display_value else self._empty_name_value

    @staticmethod
    def _module_id_for_requirement(requirement_id, permit_id):
        """The module id of the permit's process_module tile that lists this
        requirement (None for a grouping parent). Scoped to the permit's tiles by
        the indexed resourceinstance_id, not a whole-table JSONB scan."""
        reference_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.PROCESS_REQUIREMENT)
        module_id_node = node_id(GraphSlugs.PERMIT_APPLICATION, pa.MODULE_ID)
        child = (
            models.TileModel.objects.filter(
                resourceinstance_id=permit_id,
                data__contains={reference_node: [{"resourceId": str(requirement_id)}]},
            )
            .select_related("parenttile")
            .first()
        )
        parent = child.parenttile if child else None
        return parent.data.get(module_id_node) if parent else None
