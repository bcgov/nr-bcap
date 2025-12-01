from arches.app.models import models
from bcap.util.aliases.site_visit import SiteVisitAliases as aliases
from bcgov_arches_common.functions.abstract_primary_descriptors import (
    AbstractPrimaryDescriptors as AbstractDescriptors,
)

details = {
    "functionid": "60000000-0000-0000-0000-000000001003",
    "name": "Site Visit Descriptors",
    "type": "primarydescriptors",
    "modulename": "site_visit_descriptors.py",
    "description": "Function that provides the primary descriptors for Site Visit resources",
    "defaultconfig": {
        "module": "bcap.functions.site_visit_descriptors",
        "class_name": "SiteVisitDescriptors",
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
    "classname": "SiteVisitDescriptors",
    "component": "views/components/functions/site-visit-descriptors",
}


class SiteVisitDescriptors(AbstractDescriptors):
    NON_PERMITTED_STRING = "Non-permit"

    # For Name part of descriptor
    AbstractDescriptors._graph_slug = "site_visit"

    AbstractDescriptors._name_node_aliases = [
        aliases.ASSOCIATED_PERMIT,
        aliases.LAST_DATE_OF_SITE_VISIT,
        aliases.AFFILIATION,
    ]

    AbstractDescriptors._card_node_aliases = [
        aliases.SITE_VISIT_TYPE,
        aliases.PROJECT_DESCRIPTION,
        aliases.ARCHAEOLOGICAL_SITE,
    ]

    # AbstractDescriptors._popup_node_aliases = AbstractDescriptors._card_node_aliases

    def get_name_descriptor(self, resource, config, context):
        tile = (
            models.TileModel.objects.filter(
                nodegroup_id=AbstractDescriptors._nodes[
                    aliases.ASSOCIATED_PERMIT
                ].nodegroup_id
            )
            .filter(resourceinstance_id=resource)
            .first()
        )

        permit = AbstractDescriptors._get_value_from_node(
            node_alias=aliases.ASSOCIATED_PERMIT,
            resourceinstanceid=resource,
            data_tile=tile,
        )
        name_values = [permit if permit else self.NON_PERMITTED_STRING]
        date = AbstractDescriptors._get_value_from_node(
            node_alias=aliases.LAST_DATE_OF_SITE_VISIT,
            resourceinstanceid=resource,
            data_tile=tile,
        )
        if date:
            name_values.append(date.replace("-", "/"))
        affiliation = AbstractDescriptors._get_value_from_node(
            node_alias=aliases.AFFILIATION,
            resourceinstanceid=resource,
            data_tile=tile,
        )
        if affiliation:
            name_values.append(affiliation)

        return " - ".join(name_values)

    def get_search_card_descriptor(self, resource, config, context):
        tiles = models.TileModel.objects.filter(
            nodegroup_id=AbstractDescriptors._nodes[
                aliases.SITE_VISIT_TYPE
            ].nodegroup_id,
            resourceinstance_id=resource,
        ).all()
        return super().get_values_in_order(
            aliases=AbstractDescriptors._card_node_aliases,
            resource=resource,
            config=config,
            tile_data=list(tiles),
        )
