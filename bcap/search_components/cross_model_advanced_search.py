import logging

from typing_extensions import Any

from arches.app.datatypes.datatypes import DataTypeFactory
from arches.app.models.models import (
    CardModel,
    CardXNodeXWidget,
    DDataType,
    GraphModel,
    Node,
    ResourceXResource,
)
from arches.app.models.system_settings import settings
from arches.app.search.components.base import BaseSearchFilter
from arches.app.search.elasticsearch_dsl_builder import Bool, Nested, Terms
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.utils.betterJSONSerializer import JSONDeserializer
from bcap.util.bcap_aliases import GraphSlugs


log = logging.getLogger(__name__)


details = {
    "classname": "CrossModelAdvancedSearch",
    "componentname": "cross-model-advanced-search",
    "componentpath": "views/components/search/cross-model-advanced-search",
    "config": {},
    "icon": "fa fa-search-plus",
    "modulename": "cross_model_advanced_search.py",
    "name": "Cross-Model Advanced Search",
    "searchcomponentid": "",
    "type": "cross-model-advanced-search-type",
}


class CrossModelAdvancedSearch(BaseSearchFilter):
    def _build_facet_query(
        self,
        advanced_filter: dict,
        datatype_factory: DataTypeFactory,
    ) -> tuple:
        graph_id = None
        null_query = Bool()
        tile_query = Bool()

        log.info(f"[CrossModel] _build_facet_query called with: {advanced_filter}")

        for key, val in advanced_filter.items():
            if key in ("graph_id", "op", "translate_to_parent"):
                if key == "graph_id":
                    graph_id = val

                continue

            if not val:
                log.debug(f"[CrossModel] Skipping empty val for key {key}")
                continue

            node = Node.objects.filter(pk=key).select_related("nodegroup").first()

            if not node:
                log.debug(f"[CrossModel] No node found for key {key}")
                continue

            if not self.request.user.has_perm("read_nodegroup", node.nodegroup):
                log.debug(f"[CrossModel] No permission for nodegroup {node.nodegroup_id}")
                continue

            if graph_id is None:
                graph_id = str(node.graph_id)

            log.info(f"[CrossModel] Processing node {node.name} ({key}), datatype={node.datatype}, val={val}")

            datatype = datatype_factory.get_instance(node.datatype)

            if datatype:
                if (
                    "op" in val
                    and (val["op"] == "null" or val["op"] == "not_null")
                ) or (
                    "val" in val
                    and (val["val"] == "null" or val["val"] == "not_null")
                ):
                    datatype.append_search_filters(val, node, null_query, self.request)
                else:
                    datatype.append_search_filters(val, node, tile_query, self.request)

                log.info(f"[CrossModel] After append_search_filters, tile_query: {tile_query.dsl}")

        if null_query.dsl["bool"]["should"]:
            tile_query.must(null_query)

        return tile_query, graph_id

    def _get_parent_resource_ids(
        self,
        child_resource_ids: list,
        parent_graph_slug: str,
    ) -> set:
        parent_graph = GraphModel.objects.filter(slug=parent_graph_slug).first()

        if not parent_graph:
            return set()

        parent_ids = set()

        rels_from = ResourceXResource.objects.filter(
            from_resource_id__in=child_resource_ids,
            to_resource__graph=parent_graph,
        ).values_list("to_resource_id", flat=True)

        parent_ids.update(str(rid) for rid in rels_from)

        rels_to = ResourceXResource.objects.filter(
            to_resource_id__in=child_resource_ids,
            from_resource__graph=parent_graph,
        ).values_list("from_resource_id", flat=True)

        parent_ids.update(str(rid) for rid in rels_to)

        return parent_ids

    def _get_parent_ids_for_facet(
        self,
        advanced_filter: dict,
        datatype_factory: DataTypeFactory,
        parent_graph_id: str,
        parent_graph_slug: str,
    ) -> set:
        tile_query, graph_id = self._build_facet_query(advanced_filter, datatype_factory)

        log.info(f"[CrossModel] Facet graph_id: {graph_id}")
        log.info(f"[CrossModel] Tile query DSL: {tile_query.dsl}")

        if not graph_id:
            log.warning("[CrossModel] No graph_id found, returning empty set")
            return set()

        has_filters = (
            tile_query.dsl["bool"]["filter"]
            or tile_query.dsl["bool"]["must"]
            or tile_query.dsl["bool"]["should"]
            or tile_query.dsl["bool"]["must_not"]
        )

        if not has_filters:
            log.warning(f"[CrossModel] No filters in tile_query for graph {graph_id}, returning empty set")
            return set()

        facet_query = Bool()
        facet_query.filter(Terms(field="graph_id", terms=[graph_id]))
        facet_query.must(Nested(path="tiles", query=tile_query))

        log.info(f"[CrossModel] Full facet query: {facet_query.dsl}")

        se = SearchEngineFactory().create()

        facet_results = se.search(
            index=RESOURCES_INDEX,
            query=facet_query.dsl,
            size=10000,
        )

        total_hits = facet_results.get("hits", {}).get("total", {})
        log.info(f"[CrossModel] Facet search returned {total_hits} hits")

        child_resource_ids = []
        parent_ids = set()

        for hit in facet_results.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            resource_id = source.get("resourceinstanceid")
            hit_graph_id = source.get("graph_id")

            if not resource_id:
                continue

            if parent_graph_id and str(hit_graph_id) == parent_graph_id:
                parent_ids.add(resource_id)
            else:
                child_resource_ids.append(resource_id)

        log.info(f"[CrossModel] Found {len(child_resource_ids)} child resources, {len(parent_ids)} direct parent matches")

        if child_resource_ids:
            translated_ids = self._get_parent_resource_ids(child_resource_ids, parent_graph_slug)
            log.info(f"[CrossModel] Translated to {len(translated_ids)} parent IDs")
            parent_ids.update(translated_ids)

        log.info(f"[CrossModel] Total parent IDs for this facet: {len(parent_ids)}")
        return parent_ids

    def _group_facets_by_graph(
        self,
        advanced_filters: list,
        datatype_factory: DataTypeFactory,
    ) -> dict:
        graph_facets = {}

        for advanced_filter in advanced_filters:
            tile_query, graph_id = self._build_facet_query(
                advanced_filter, datatype_factory
            )

            if not graph_id:
                continue

            has_filters = (
                tile_query.dsl["bool"]["filter"]
                or tile_query.dsl["bool"]["must"]
                or tile_query.dsl["bool"]["should"]
                or tile_query.dsl["bool"]["must_not"]
            )

            if not has_filters:
                continue

            op = advanced_filter.get("op", "and")

            if graph_id not in graph_facets:
                graph_facets[graph_id] = []

            graph_facets[graph_id].append((tile_query, op))

        return graph_facets

    def append_dsl(self, search_query_object: dict, **kwargs: Any) -> None:
        querystring_params = kwargs.get("querystring", "[]")
        advanced_filters = JSONDeserializer().deserialize(querystring_params)

        if not advanced_filters:
            return

        translate_to_parent = any(
            f.get("translate_to_parent", False)
            for f in advanced_filters
        )

        if translate_to_parent:
            return

        datatype_factory = DataTypeFactory()
        graph_facets = self._group_facets_by_graph(advanced_filters, datatype_factory)

        if not graph_facets:
            return

        cross_model_query = Bool()

        for graph_id, facets in graph_facets.items():
            graph_query = Bool()

            for tile_query, op in facets:
                nested_query = Nested(path="tiles", query=tile_query)
                if op == "or":
                    graph_query.should(nested_query)
                else:
                    graph_query.must(nested_query)

            if graph_query.dsl["bool"]["should"]:
                graph_query.dsl["bool"]["minimum_should_match"] = 1

            graph_with_filter = Bool()
            graph_with_filter.filter(Terms(field="graph_id", terms=[graph_id]))
            graph_with_filter.must(graph_query)

            cross_model_query.should(graph_with_filter)

        if cross_model_query.dsl["bool"]["should"]:
            cross_model_query.dsl["bool"]["minimum_should_match"] = 1

        has_query = (
            cross_model_query.dsl["bool"]["must"]
            or cross_model_query.dsl["bool"]["should"]
        )

        if has_query:
            search_query_object["query"].add_query(cross_model_query)

    def post_search_hook(
        self,
        search_query_object: dict,
        response_object: dict,
        **kwargs: Any,
    ) -> None:
        advanced_filters_raw = self.request.GET.get("cross-model-advanced-search", "[]")
        advanced_filters = JSONDeserializer().deserialize(advanced_filters_raw)

        log.info(f"[CrossModel] post_search_hook called with {len(advanced_filters)} filters")

        translate_to_parent = any(
            f.get("translate_to_parent", False) for f in advanced_filters
        )

        if not translate_to_parent:
            log.info("[CrossModel] translate_to_parent is False, skipping post_search_hook")
            return

        parent_graph_slug = GraphSlugs.ARCHAEOLOGICAL_SITE
        parent_graph = GraphModel.objects.filter(slug=parent_graph_slug).first()
        parent_graph_id = str(parent_graph.graphid) if parent_graph else None

        log.info(f"[CrossModel] Parent graph: {parent_graph_slug} ({parent_graph_id})")

        datatype_factory = DataTypeFactory()
        combined_parent_ids = None

        for idx, advanced_filter in enumerate(advanced_filters):
            log.info(f"[CrossModel] Processing facet {idx}: graph_id={advanced_filter.get('graph_id')}, op={advanced_filter.get('op')}")

            facet_parent_ids = self._get_parent_ids_for_facet(
                advanced_filter,
                datatype_factory,
                parent_graph_id,
                parent_graph_slug,
            )

            op = advanced_filter.get("op", "and")

            if combined_parent_ids is None:
                combined_parent_ids = facet_parent_ids
                log.info(f"[CrossModel] Initial set: {len(combined_parent_ids)} parent IDs")
            elif op == "or":
                before = len(combined_parent_ids)
                combined_parent_ids = combined_parent_ids.union(facet_parent_ids)
                log.info(f"[CrossModel] After OR: {before} -> {len(combined_parent_ids)} parent IDs")
            else:
                before = len(combined_parent_ids)
                combined_parent_ids = combined_parent_ids.intersection(facet_parent_ids)
                log.info(f"[CrossModel] After AND: {before} -> {len(combined_parent_ids)} parent IDs")

        if not combined_parent_ids:
            log.info("[CrossModel] No combined parent IDs, returning empty results")
            response_object["results"]["hits"]["hits"] = []
            response_object["results"]["hits"]["total"]["value"] = 0
            response_object["total_results"] = 0
            return

        log.info(f"[CrossModel] Final: {len(combined_parent_ids)} parent IDs to fetch")

        se = SearchEngineFactory().create()

        parent_query = Bool()
        parent_query.filter(Terms(field="resourceinstanceid", terms=list(combined_parent_ids)))

        parent_results = se.search(
            index=RESOURCES_INDEX,
            query=parent_query.dsl,
            size=len(combined_parent_ids),
        )

        parent_hits = parent_results.get("hits", {}).get("hits", [])
        log.info(f"[CrossModel] Parent search returned {len(parent_hits)} hits")

        for hit in parent_hits:
            source = hit.get("_source", {})
            displayname = source.get("displayname")

            if isinstance(displayname, list) and displayname:
                source["displayname"] = displayname[0].get("value", "")

            displaydescription = source.get("displaydescription")

            if isinstance(displaydescription, list) and displaydescription:
                source["displaydescription"] = displaydescription[0].get("value", "")

        response_object["results"]["hits"]["hits"] = parent_hits
        response_object["results"]["hits"]["total"] = {
            "relation": "eq",
            "value": len(parent_hits),
        }
        response_object["total_results"] = len(parent_hits)

        parent_filter = Bool()
        parent_filter.filter(Terms(field="resourceinstanceid", terms=list(combined_parent_ids)))
        search_query_object["query"].dsl = {"query": parent_filter.dsl}

    def view_data(self) -> dict:
        ret = {}

        resource_graphs = (
            GraphModel.objects.exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(isresource=False)
            .exclude(is_active=False)
            .exclude(source_identifier__isnull=False)
        )

        searchable_datatypes = [
            d.pk for d in DDataType.objects.filter(issearchable=True)
        ]

        searchable_nodes = Node.objects.filter(
            graph__isresource=True,
            graph__is_active=True,
            datatype__in=searchable_datatypes,
            issearchable=True,
        )

        resource_cards = CardModel.objects.filter(
            graph__isresource=True,
            graph__is_active=True,
        ).select_related("nodegroup")

        cardwidgets = CardXNodeXWidget.objects.filter(node__in=searchable_nodes)
        datatypes = DDataType.objects.all()

        searchable_cards = []

        for card in resource_cards:
            if self.request.user.has_perm("read_nodegroup", card.nodegroup):
                searchable_cards.append(card)

        ret["graphs"] = resource_graphs
        ret["datatypes"] = datatypes
        ret["nodes"] = searchable_nodes
        ret["cards"] = searchable_cards
        ret["cardwidgets"] = cardwidgets

        return ret
