from arches.app.models import models
from bcap.util.bcap_aliases import GraphSlugs, LegislativeActAliases
from bcap.util.aliases.archaeological_site import (
    ArchaeologicalSiteAliases as BCAPSiteAliases,
)
from bcap.util.aliases.hria_discontinued_data import HriaDiscontinuedDataAliases
from bcap.util.aliases.site_visit import SiteVisitAliases
from bcgov_arches_common.util.graph_lookup import GraphLookup
from arches.settings import LANGUAGE_CODE


class BusinessDataProxy:
    _graph_lookup = None

    def __init__(self, graph_slug, node_aliases):
        self._graph_lookup = GraphLookup(graph_slug, node_aliases)

    def get_value_from_node(
        self,
        alias,
        resourceinstanceid=None,
        data_tile=None,
        context=None,
        use_boolean_label=True,
    ):
        """
        get the values from the resource tile(s) for the node with the given name

        Keyword Arguments

        alias     -- node alias of the data to extract
        resourceinstanceid -- id of resource instance used to fetch the tile(s) if data_tile not specified
        data_tile -- if specified, the tile to extract the value from
        context -- if specified, context with the target language
        use_boolean_label -- If true, for boolean datatypes, returns the associated label, otherwise use raw value
        """
        node = self._graph_lookup.get_node(alias)
        datatype = self._graph_lookup.get_datatype(alias)

        if node is None or datatype is None:
            return None

        display_values = []

        if context is not None and "language" in context:
            language = context["language"]
        else:
            language = LANGUAGE_CODE

        tiles = (
            [data_tile]
            if data_tile
            else models.TileModel.objects.filter(nodegroup_id=node.nodegroup_id).filter(
                resourceinstance_id=resourceinstanceid
            )
        )

        for tile in tiles:
            if tile:
                if (
                    node.datatype == "boolean"
                    and use_boolean_label
                    and "trueLabel" in node.config
                ):
                    value = (datatype.get_tile_data(tile))[str(node.nodeid)]
                    if value is None:
                        return None
                    else:
                        display_values.append(
                            node.config["trueLabel"][language]
                            if (datatype.get_tile_data(tile))[str(node.nodeid)]
                            else node.config["falseLabel"][language]
                        )
                else:
                    display_values.append(
                        datatype.get_display_value(tile, node, language=language)
                    )
        return (
            None
            if len(display_values) == 0
            else (display_values[0] if len(display_values) == 1 else display_values)
        )


class SiteVisitDataProxy(BusinessDataProxy):
    def __init__(self):
        super(SiteVisitDataProxy, self).__init__(
            GraphSlugs.SITE_VISIT, SiteVisitAliases.get_aliases().values()
        )


class HriaDiscontinuedDataProxy(BusinessDataProxy):
    def __init__(self):
        super(HriaDiscontinuedDataProxy, self).__init__(
            GraphSlugs.HRIA_DISCONTINUED_DATA,
            HriaDiscontinuedDataAliases.get_aliases().values(),
        )


class ArchaeologicalSiteDataProxy(BusinessDataProxy):

    def __init__(self):
        super(ArchaeologicalSiteDataProxy, self).__init__(
            GraphSlugs.ARCHAEOLOGICAL_SITE, BCAPSiteAliases.get_aliases().values()
        )

    def get_related_resources(
        self,
        arch_site_resourceinstanceid,
        related_resource_graph_slug,
        related_resource_node_alias=None,
    ):
        arch_site_graph = models.Graph.objects.get(
            slug=GraphSlugs.ARCHAEOLOGICAL_SITE, source_identifier_id__isnull=True
        )
        related_resource_graph = models.Graph.objects.get(
            slug=related_resource_graph_slug, source_identifier_id__isnull=True
        )
        site_visits = (
            models.ResourceXResource.objects.filter(
                to_resource=arch_site_resourceinstanceid,
                from_resource_graph_id=related_resource_graph.graphid,
                to_resource_graph_id=arch_site_graph.graphid,
            )
            .select_related("from_resource")
            .all()
        )
        return [visit.from_resource for visit in site_visits]

    def is_site_public(self, resourceinstance):
        return (
            self.get_value_from_node(
                BCAPSiteAliases.RESTRICTED,
                resourceinstanceid=resourceinstance.resourceinstanceid,
                use_boolean_label=False,
            )
            != "True"
            and self.get_value_from_node(
                BCAPSiteAliases.OFFICIALLY_RECOGNIZED_SITE,
                resourceinstanceid=resourceinstance.resourceinstanceid,
                use_boolean_label=False,
            )
            == "True"
            and (
                self.get_value_from_node(
                    BCAPSiteAliases.BCAP_SUBMISSION_STATUS,
                    resourceinstanceid=resourceinstance.resourceinstanceid,
                )
                in ["Approved - Full Record", "Approved - Basic Record"]
            )
            and (
                self.get_value_from_node(
                    BCAPSiteAliases.REGISTRATION_STATUS,
                    resourceinstanceid=resourceinstance.resourceinstanceid,
                )
                in ["Registered", "Federal Jurisdiction"]
            )
        )


class LegislativeActDataProxy(BusinessDataProxy):

    def __init__(self):
        super(LegislativeActDataProxy, self).__init__(
            GraphSlugs.LEGISLATIVE_ACT, LegislativeActAliases.get_aliases().values()
        )

    def get_authorities(self, legislative_act_ids):
        values = []
        act_ids = (
            [legislative_act_ids]
            if type(legislative_act_ids) is str
            else legislative_act_ids
        )
        tiles = models.TileModel.objects.filter(
            nodegroup_id=self._graph_lookup.get_node(
                LegislativeActAliases.AUTHORITY
            ).nodegroup_id,
            resourceinstance_id__in=act_ids,
        ).all()
        # Need to convert to string to get it from the tile data map
        recognition_type_nodeid = str(
            self._graph_lookup.get_node(LegislativeActAliases.RECOGNITION_TYPE).nodeid
        )
        for tile in tiles:
            values.append(
                {
                    LegislativeActAliases.AUTHORITY: self.get_value_from_node(
                        LegislativeActAliases.AUTHORITY, data_tile=tile
                    ),
                    LegislativeActAliases.LEGAL_INSTRUMENT: self.get_value_from_node(
                        LegislativeActAliases.LEGAL_INSTRUMENT, data_tile=tile
                    ),
                    LegislativeActAliases.ACT_SECTION: self.get_value_from_node(
                        LegislativeActAliases.ACT_SECTION, data_tile=tile
                    ),
                    LegislativeActAliases.RECOGNITION_TYPE: self.get_value_from_node(
                        LegislativeActAliases.RECOGNITION_TYPE, data_tile=tile
                    ),
                    (
                        "%s_definition" % LegislativeActAliases.RECOGNITION_TYPE
                    ): LegislativeActDataProxy.get_recognition_definition(
                        tile.data[recognition_type_nodeid]
                    ),
                }
            )
        values = list(filter(lambda val: val is not None, values))
        return values

    @staticmethod
    def get_recognition_definition(valueid):
        if valueid:
            value = models.Value.objects.get(valueid=valueid)
            definition_value = models.Value.objects.filter(
                concept_id=value.concept_id, valuetype="definition"
            ).first()
            if definition_value:
                return definition_value
