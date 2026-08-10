from arches.app.models import models
from bcgov_arches_common.functions.abstract_primary_descriptors import (
    AbstractPrimaryDescriptors,
)
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


class BCAPSiteDescriptors(AbstractPrimaryDescriptors):
    _graph_slug = "archaeological_site"

    _empty_name_value = "(No official name)"

    _name_node_aliases = [aliases.BORDEN_NUMBER]
    _sig_event_nodes = [
        aliases.DECISION_REGISTRATION_STATUS,
        aliases.TYPOLOGY_CLASS,
    ]
    _popup_node_aliases = [
        aliases.DECISION_REGISTRATION_STATUS,
        aliases.NAME,
        "typologies",
    ]
    _card_node_aliases = [
        aliases.DECISION_REGISTRATION_STATUS,
        aliases.NAME,
        "typologies",
    ]
    _address_nodes = [
        [aliases.STREET_NUMBER, aliases.STREET_NAME],
        [aliases.CITY, "postal_code"],
    ]

    @classmethod
    def get_all_nodes(cls):
        """Also loads the significant-event and address nodes, which are read by
        the typology and address descriptors rather than by alias order."""
        return (
            super().get_all_nodes() + cls._sig_event_nodes + sum(cls._address_nodes, [])
        )

    def get_primary_descriptor_from_nodes(
        self, resource, config, context=None, descriptor=None
    ):
        self.ensure_initialized()

        return_value = ""
        display_values = {}

        try:
            if config["type"] == "name":
                return self._get_site_name(resource)

            _description_order = (
                self._popup_node_aliases
                if config["type"] == "map_popup"
                else self._card_node_aliases
            )

            nodes = self._nodes

            for node_alias in _description_order:
                value = self._get_value_from_node(node_alias, resource)
                if value:
                    if config["first_only"]:
                        return self._format_value(nodes[node_alias].name, value, config)
                    display_values[node_alias] = value

            for alias in _description_order:
                if alias == "address":
                    return_value += self._format_value(
                        "Address", self._get_address(resource), config
                    )
                elif alias == "typologies":
                    typology_classes, typology_values = self._get_typologies(
                        resource.resourceinstanceid
                    )
                    return_value += self._format_value(
                        "Site Class", typology_classes, config
                    )
                    return_value += self._format_value(
                        "Descriptor", typology_values, config
                    )
                elif (
                    alias == aliases.DECISION_REGISTRATION_STATUS
                    and alias in display_values
                ):
                    return_value += self._format_value(
                        "Registration Status", display_values[alias], config
                    )
                elif alias in display_values:
                    return_value += self._format_value(
                        nodes[alias].name, display_values[alias], config
                    )

            return return_value

        except ValueError as e:
            print(e, "invalid nodegroupid participating in descriptor function.")

    @classmethod
    def _get_typologies(cls, resourceinstanceid):
        datatype = cls._datatypes[aliases.TYPOLOGY_CLASS]
        typology_values = []
        typology_classes = set()
        tiles = (
            models.TileModel.objects.filter(
                nodegroup_id=cls._nodes[aliases.TYPOLOGY_CLASS].nodegroup_id
            )
            .filter(resourceinstance_id=resourceinstanceid)
            .all()
        )

        for tile in tiles:
            if tile:
                ref_value = datatype.to_python(
                    tile.data[str(cls._nodes[aliases.TYPOLOGY_CLASS].nodeid)]
                )
                typology_values.append(
                    datatype.get_display_value(tile, cls._nodes[aliases.TYPOLOGY_CLASS])
                )
                typology_class = get_hierarchy_for_list_item(
                    ref_value[0].labels[0].list_item_id
                )
                typology_classes.add(
                    typology_class[0] if len(typology_class) > 0 else None
                )

        return list(typology_classes), typology_values

    @classmethod
    def _get_address(cls, resource):
        address = ""
        nodes = cls._nodes

        for address_line_nodes in cls._address_nodes:
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
                display_value = cls._get_value_from_node(
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
        borden_number_datatype = cls._datatypes[aliases.BORDEN_NUMBER]
        display_value = ""

        borden_number_tile = models.TileModel.objects.filter(
            nodegroup_id=cls._nodes[aliases.BORDEN_NUMBER].nodegroup_id,
            resourceinstance_id=resource.resourceinstanceid,
        ).first()

        if borden_number_tile:
            display_value += "%s" % borden_number_datatype.get_display_value(
                borden_number_tile, cls._nodes[aliases.BORDEN_NUMBER]
            )

        return display_value if display_value else self._empty_name_value
