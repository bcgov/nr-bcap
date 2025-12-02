from arches.app.functions.primary_descriptors import AbstractPrimaryDescriptorsFunction
from arches.app.models import models
from arches.app.datatypes.datatypes import DataTypeFactory
from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases as aliases
from bcap.util.controlled_list import get_hierarchy_for_list_item

details = {
    "functionid": "60000000-0000-0000-0000-000000001002",
    "name": "BCAP Site Descriptors",
    "type": "primarydescriptors",
    "modulename": "bcap_site_descriptors.py",
    "description": "Function that provides the primary descriptors for BC Heritage Resources",
    "defaultconfig": {
        "module": "arches_bcap.functions.bcap_site_descriptors",
        "class_name": "BCAPSiteDescriptors",
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
    "classname": "BCAPSiteDescriptors",
    "component": "views/components/functions/bcap-site-descriptors",
}


class BCAPSiteDescriptors(AbstractPrimaryDescriptorsFunction):
    _datatype_factory = DataTypeFactory()
    # For Name part of descriptor
    graph_slug = "archaeological_site"

    _empty_name_value = "(No official name)"
    _nodes = {}
    _datatypes = {}

    _initialized = False

    # @todo Change these to aliases
    _name_nodes = [aliases.BORDEN_NUMBER]
    _sig_event_nodes = [
        aliases.REGISTRATION_STATUS,
        aliases.TYPOLOGY_CLASS,
    ]
    _popup_nodes = [aliases.CITY, "address"]
    _card_nodes = [aliases.REGISTRATION_STATUS, aliases.NAME, "typologies"]
    _address_nodes = [
        [aliases.STREET_NUMBER, aliases.STREET_NAME],
        [aliases.CITY, "postal_code"],
    ]

    # Initializes the static nodes and datatypes data
    def initialize(self):
        for alias in (
            BCAPSiteDescriptors._name_nodes
            + BCAPSiteDescriptors._sig_event_nodes
            + BCAPSiteDescriptors._popup_nodes
            + BCAPSiteDescriptors._card_nodes
            + sum(BCAPSiteDescriptors._address_nodes, [])
        ):
            node = models.Node.objects.filter(
                alias=alias,
                graph__slug=BCAPSiteDescriptors.graph_slug,
                source_identifier__isnull=True,
            ).first()
            if node:
                BCAPSiteDescriptors._nodes[alias] = node
                BCAPSiteDescriptors._datatypes[alias] = (
                    BCAPSiteDescriptors._datatype_factory.get_instance(node.datatype)
                )

        BCAPSiteDescriptors._initialized = True

    def get_primary_descriptor_from_nodes(
        self, resource, config, context=None, descriptor=None
    ):
        if not BCAPSiteDescriptors._initialized:
            self.initialize()

        return_value = ""
        display_values = {}

        try:
            if config["type"] == "name":
                return self._get_site_name(resource)

            _description_order = (
                self._popup_nodes if config["type"] == "map_popup" else self._card_nodes
            )

            nodes = BCAPSiteDescriptors._nodes

            for node_alias in _description_order:
                value = BCAPSiteDescriptors._get_value_from_node(node_alias, resource)
                if value:
                    if config["first_only"]:
                        return BCAPSiteDescriptors._format_value(
                            nodes[node_alias].name, value, config
                        )
                    display_values[node_alias] = value

            for alias in _description_order:
                if alias == "address":
                    return_value += BCAPSiteDescriptors._format_value(
                        "Address", BCAPSiteDescriptors._get_address(resource), config
                    )
                elif alias == "typologies":
                    typology_classes, typology_values = (
                        BCAPSiteDescriptors._get_typologies(resource.resourceinstanceid)
                    )
                    return_value += BCAPSiteDescriptors._format_value(
                        "Site Class", typology_classes, config
                    )
                    return_value += BCAPSiteDescriptors._format_value(
                        "Descriptor", typology_values, config
                    )
                elif alias in display_values:
                    return_value += BCAPSiteDescriptors._format_value(
                        nodes[alias].name, display_values[alias], config
                    )

            return return_value

        except ValueError as e:
            print(e, "invalid nodegroupid participating in descriptor function.")

    @staticmethod
    def _get_typologies(resourceinstanceid):
        datatype = BCAPSiteDescriptors._datatypes[aliases.TYPOLOGY_CLASS]
        typology_values = []
        typology_classes = set()
        tiles = (
            models.TileModel.objects.filter(
                nodegroup_id=BCAPSiteDescriptors._nodes[
                    aliases.TYPOLOGY_CLASS
                ].nodegroup_id
            )
            .filter(resourceinstance_id=resourceinstanceid)
            .all()
        )

        for tile in tiles:
            if tile:
                ref_value = datatype.to_python(
                    tile.data[
                        str(BCAPSiteDescriptors._nodes[aliases.TYPOLOGY_CLASS].nodeid)
                    ]
                )
                typology_values.append(
                    datatype.get_display_value(
                        tile, BCAPSiteDescriptors._nodes[aliases.TYPOLOGY_CLASS]
                    )
                )
                typology_class = get_hierarchy_for_list_item(
                    ref_value[0].labels[0].list_item_id
                )
                typology_classes.add(
                    typology_class[0] if len(typology_class) > 0 else None
                )

        return list(typology_classes), typology_values

    @staticmethod
    def _get_value_from_node(node_alias, resourceinstanceid=None, data_tile=None):
        """
        get the display value from the resource tile(s) for the node with the given name

        Keyword Arguments

        node_alias -- node alias of the data to extract
        resourceinstanceid -- id of resource instance used to fetch the tile(s) if data_tile not specified
        data_tile -- if specified, the tile to extract the value from
        """
        if node_alias not in BCAPSiteDescriptors._nodes:
            return None

        display_values = []
        datatype = BCAPSiteDescriptors._datatypes[node_alias]

        tiles = (
            [data_tile]
            if data_tile
            else models.TileModel.objects.filter(
                nodegroup_id=BCAPSiteDescriptors._nodes[node_alias].nodegroup_id
            )
            .filter(resourceinstance_id=resourceinstanceid)
            .all()
        )

        for tile in tiles:
            if tile:
                display_values.append(
                    datatype.get_display_value(
                        tile, BCAPSiteDescriptors._nodes[node_alias]
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

    @staticmethod
    def _get_address(resource):
        address = ""
        nodes = BCAPSiteDescriptors._nodes

        for address_line_nodes in BCAPSiteDescriptors._address_nodes:
            if address:
                address += "<br>"
            line = ""
            for address_node_alias in address_line_nodes:
                tile = (
                    models.TileModel.objects.filter(
                        nodegroup_id=nodes[address_node_alias].nodegroup_id
                    )
                    .filter(resourceinstance_id=resource.resourceinstanceid)
                    .first()
                )
                if line:
                    line += " "
                display_value = BCAPSiteDescriptors._get_value_from_node(
                    node_alias=address_node_alias, data_tile=tile
                )
                display_value = (
                    display_value[0] if type(display_value) is list else display_value
                )
                line += display_value if display_value is not None else ""
            if line:
                address += line
        return address if address else None

    def _get_site_name(self, resource):
        # name_datatype = BCAPSiteDescriptors._datatypes[aliases.NAME]
        # name_type_datatype = BCAPSiteDescriptors._datatypes[aliases.NAME_TYPE]
        borden_number_datatype = BCAPSiteDescriptors._datatypes[aliases.BORDEN_NUMBER]
        display_value = ""
        #
        # for tile in (
        #     models.TileModel.objects.filter(
        #         nodegroup_id=BCAPSiteDescriptors._nodes[aliases.NAME].nodegroup_id
        #     )
        #     .filter(resourceinstance_id=resource.resourceinstanceid)
        #     .all()
        # ):
        #     if (
        #         name_type_datatype.get_display_value(
        #             tile, BCAPSiteDescriptors._nodes[aliases.NAME_TYPE]
        #         )
        #         == "Common"
        #     ):
        #         name = name_datatype.get_display_value(
        #             tile, BCAPSiteDescriptors._nodes[aliases.NAME]
        #         )
        #         if display_value and name:
        #             display_value = display_value + ",<br>"
        #         if name:
        #             display_value = display_value + name
        #
        # if not display_value:
        #     display_value = self._empty_name_value

        borden_number_tile = models.TileModel.objects.filter(
            nodegroup_id=BCAPSiteDescriptors._nodes[aliases.BORDEN_NUMBER].nodegroup_id,
            resourceinstance_id=resource.resourceinstanceid,
        ).first()

        if borden_number_tile:
            display_value += "%s" % borden_number_datatype.get_display_value(
                borden_number_tile, BCAPSiteDescriptors._nodes[aliases.BORDEN_NUMBER]
            )

        return display_value if display_value else self._empty_name_value
