import logging

from arches.app.models import models
from bcgov_arches_common.functions.abstract_primary_descriptors import (
    AbstractPrimaryDescriptors,
)
from bcap.util.aliases.archaeological_site import ArchaeologicalSiteAliases as aliases
from bcap.util.bcap_aliases import GraphSlugs
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
    _graph_slug = GraphSlugs.ARCHAEOLOGICAL_SITE

    _empty_name_value = "(No official name)"

    _name_node_aliases = [aliases.BORDEN_NUMBER]
    _sig_event_nodes = [
        aliases.DECISION_REGISTRATION_STATUS,
        aliases.TYPOLOGY_CLASS,
    ]
    # Real node aliases only: the base looks every one of these up on the graph.
    # The typology block is appended after them, in _descriptor_for.
    _popup_node_aliases = [
        aliases.DECISION_REGISTRATION_STATUS,
        aliases.NAME,
    ]
    _card_node_aliases = [
        aliases.DECISION_REGISTRATION_STATUS,
        aliases.NAME,
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
        the registration status is relabelled, and the typology block is
        derived from tiles rather than read off a node."""
        return_value = ""

        try:
            for alias in alias_order:
                value = self._get_value_from_node(alias, resource)
                if not value:
                    continue
                label = (
                    "Registration Status"
                    if alias == aliases.DECISION_REGISTRATION_STATUS
                    else self._nodes[alias].name
                )
                formatted = self._format_value(
                    label, value, config, alias in self._html_nodes
                )
                if config["first_only"]:
                    return formatted
                return_value += formatted

            typology_classes, typology_values = self._get_typologies(
                resource.resourceinstanceid
            )
            for label, values in (
                ("Site Class", typology_classes),
                ("Descriptor", typology_values),
            ):
                # The base's _format_value wraps even an empty value in the
                # label template, so an absent typology would otherwise render
                # as a stray empty label.
                if not values:
                    continue
                formatted = self._format_value(label, values, config)
                if config["first_only"]:
                    return formatted
                return_value += formatted

            return return_value

        except ValueError:
            logger.exception("invalid nodegroupid participating in descriptor function")
            return ""

    @classmethod
    def _get_typologies(cls, resourceinstanceid):
        node = cls._nodes[aliases.TYPOLOGY_CLASS]
        datatype = cls._datatypes[aliases.TYPOLOGY_CLASS]
        typology_values = []
        typology_classes = set()

        tiles = models.TileModel.objects.filter(
            nodegroup_id=node.nodegroup_id,
            resourceinstance_id=resourceinstanceid,
        )

        for tile in tiles:
            ref_value = datatype.to_python(tile.data[str(node.nodeid)])
            typology_values.append(datatype.get_display_value(tile, node))
            hierarchy = get_hierarchy_for_list_item(ref_value[0].labels[0].list_item_id)
            # A class with no hierarchy contributes nothing: a None in here
            # would blow up the sort in the base's _format_value.
            if hierarchy:
                typology_classes.add(hierarchy[0])

        return list(typology_classes), typology_values

    @classmethod
    def _get_site_name(cls, resource):
        node = cls._nodes[aliases.BORDEN_NUMBER]
        tile = models.TileModel.objects.filter(
            nodegroup_id=node.nodegroup_id,
            resourceinstance_id=resource.resourceinstanceid,
        ).first()
        if not tile:
            return cls._empty_name_value

        display_value = cls._datatypes[aliases.BORDEN_NUMBER].get_display_value(
            tile, node
        )
        return display_value or cls._empty_name_value
