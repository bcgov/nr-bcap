import logging

from arches.app.models import models
from bcgov_arches_common.functions.abstract_primary_descriptors import (
    AbstractPrimaryDescriptors,
)
from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases as aliases
from bcap.util.controlled_list import get_hierarchy_for_list_item

logger = logging.getLogger(__name__)

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

    @classmethod
    def get_all_nodes(cls):
        """Also loads the significant-event nodes, which the typology descriptor
        reads directly rather than by alias order."""
        return super().get_all_nodes() + cls._sig_event_nodes

    def get_name_descriptor(self, resource, config, context):
        return self._get_site_name(resource)

    def get_search_card_descriptor(self, resource, config, context):
        return self._descriptor_for(self._card_node_aliases, resource, config)

    def get_map_popup_descriptor(self, resource, config, context):
        return self._descriptor_for(self._popup_node_aliases, resource, config)

    def _descriptor_for(self, alias_order, resource, config):
        """Card and popup share one body. Not the base's get_values_in_order:
        typologies is a pseudo-alias assembled from two derived values, and the
        registration status is relabelled."""
        return_value = ""
        display_values = {}

        try:
            for node_alias in alias_order:
                # A pseudo-alias has no node, so this returns None and it falls
                # through to its own branch below.
                value = self._get_value_from_node(node_alias, resource)
                if value:
                    if config["first_only"]:
                        return self._format_value(
                            self._nodes[node_alias].name,
                            value,
                            config,
                            node_alias in self._html_nodes,
                        )
                    display_values[node_alias] = value

            for alias in alias_order:
                if alias == "typologies":
                    typology_classes, typology_values = self._get_typologies(
                        resource.resourceinstanceid
                    )
                    # The base's _format_value wraps even an empty value in the
                    # label template, so an absent typology would render as a
                    # stray empty label. Every other branch is already guarded
                    # by only storing truthy values in display_values.
                    if typology_classes:
                        return_value += self._format_value(
                            "Site Class", typology_classes, config
                        )
                    if typology_values:
                        return_value += self._format_value(
                            "Descriptor", typology_values, config
                        )
                elif alias not in display_values:
                    continue
                elif alias == aliases.DECISION_REGISTRATION_STATUS:
                    return_value += self._format_value(
                        "Registration Status",
                        display_values[alias],
                        config,
                        alias in self._html_nodes,
                    )
                else:
                    return_value += self._format_value(
                        self._nodes[alias].name,
                        display_values[alias],
                        config,
                        alias in self._html_nodes,
                    )

            return return_value

        except ValueError:
            logger.exception("invalid nodegroupid participating in descriptor function")
            return ""

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
    def _get_site_name(cls, resource):
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

        return display_value if display_value else cls._empty_name_value
