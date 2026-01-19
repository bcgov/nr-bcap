import hashlib

from typing_extensions import Any

from django.core.cache import cache
from django.db.models import Q

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
from arches.app.utils.pagination import get_paginator
from bcap.util.bcap_aliases import GraphSlugs


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

CACHE_TIMEOUT = 300


class CrossModelAdvancedSearch(BaseSearchFilter):
    _query_data = None
    _site_visit_graph_id = None

    def _add_permission_properties(self, hits: list) -> None:
        user = self.request.user

        for hit in hits:
            resource_id = hit.get("_id") or hit.get("_source", {}).get("resourceinstanceid")

            if not resource_id:
                hit["can_read"] = False
                hit["can_edit"] = False
                hit["is_principal"] = False
                continue

            hit["can_read"] = user.has_perm("view_resourceinstance", resource_id)
            hit["can_edit"] = user.has_perm("change_resourceinstance", resource_id)
            hit["is_principal"] = user.has_perm("view_resourceinstance", resource_id)

    def _build_card_query(
        self,
        card_data: dict,
        datatype_factory: DataTypeFactory,
    ) -> Bool:
        tile_query = Bool()
        filters = card_data.get("filters", {})

        for node_id, filter_value in filters.items():
            if not filter_value:
                continue

            if isinstance(filter_value, dict):
                val = filter_value.get("val", "")
                if not val and val != 0 and val:
                    continue

            node = Node.objects.filter(pk=node_id).select_related("nodegroup").first()

            if not node:
                continue

            datatype = datatype_factory.get_instance(node.datatype)

            if hasattr(datatype, "append_search_filters"):
                datatype.append_search_filters(filter_value, node, tile_query, self.request)

        return tile_query

    def _build_group_query(
        self,
        group_data: dict,
        datatype_factory: DataTypeFactory,
    ) -> Bool:
        group_query = Bool()
        match_type = group_data.get("match", "all")
        cards = group_data.get("cards", [])

        for card_data in cards:
            tile_query = self._build_card_query(card_data, datatype_factory)

            has_filters = (
                tile_query.dsl["bool"]["must"]
                or tile_query.dsl["bool"]["should"]
                or tile_query.dsl["bool"]["must_not"]
            )

            if not has_filters:
                continue

            nested_query = Nested(path="tiles", query=tile_query)

            if match_type == "any":
                group_query.should(nested_query)
            else:
                group_query.must(nested_query)

        if group_query.dsl["bool"]["should"]:
            group_query.dsl["bool"]["minimum_should_match"] = 1

        return group_query

    def _build_section_query(
        self,
        section_data: dict,
        datatype_factory: DataTypeFactory,
    ) -> Bool:
        section_query = Bool()
        groups = section_data.get("groups", [])

        for idx, group_data in enumerate(groups):
            group_query = self._build_group_query(group_data, datatype_factory)

            has_filters = (
                group_query.dsl["bool"]["must"]
                or group_query.dsl["bool"]["should"]
            )

            if not has_filters:
                continue

            if idx == 0:
                section_query.must(group_query)
            else:
                prev_operator = groups[idx - 1].get("operator_after", "and")
                if prev_operator == "or":
                    section_query.should(group_query)
                else:
                    section_query.must(group_query)

        if section_query.dsl["bool"]["should"]:
            section_query.dsl["bool"]["minimum_should_match"] = 1

        return section_query

    def _get_cache_key(self, raw_data: dict) -> str:
        cache_data = {
            "sections": raw_data.get("sections", []),
            "translate_mode": raw_data.get("translate_mode", "none"),
            "user_id": self.request.user.id,
        }
        data_str = str(cache_data)
        return f"cross_model_search_{hashlib.md5(data_str.encode()).hexdigest()}"

    def _get_pagination_params(self) -> tuple:
        page_param = self.request.GET.get("paging-filter") or self.request.POST.get("paging-filter") or "1"
        page = 1 if page_param == "" else int(page_param)
        per_page = settings.SEARCH_ITEMS_PER_PAGE
        start = per_page * (page - 1)

        return page, per_page, start

    def _get_parent_ids_for_resources(
        self,
        resource_ids: set,
        graph_id: str,
        parent_graph_id: str,
    ) -> set:
        if not resource_ids:
            return set()

        if graph_id == parent_graph_id:
            return resource_ids

        resource_ids_list = list(resource_ids)

        direct_relationships = ResourceXResource.objects.filter(
            Q(from_resource_id__in=resource_ids_list, to_resource_graph_id=parent_graph_id) |
            Q(to_resource_id__in=resource_ids_list, from_resource_graph_id=parent_graph_id)
        ).values_list("from_resource_id", "to_resource_id", "from_resource_graph_id")

        parent_ids = set()

        for from_id, to_id, from_graph_id in direct_relationships:
            if str(from_graph_id) == parent_graph_id:
                parent_ids.add(str(from_id))
            else:
                parent_ids.add(str(to_id))

        if self._site_visit_graph_id is None:
            site_visit_graph = GraphModel.objects.filter(slug=GraphSlugs.SITE_VISIT).only("graphid").first()
            self._site_visit_graph_id = str(site_visit_graph.graphid) if site_visit_graph else ""

        if self._site_visit_graph_id:
            site_visit_relationships = ResourceXResource.objects.filter(
                Q(from_resource_id__in=resource_ids_list, to_resource_graph_id=self._site_visit_graph_id) |
                Q(to_resource_id__in=resource_ids_list, from_resource_graph_id=self._site_visit_graph_id) |
                Q(from_resource_id__in=resource_ids_list, from_resource_graph_id=self._site_visit_graph_id) |
                Q(to_resource_id__in=resource_ids_list, to_resource_graph_id=self._site_visit_graph_id)
            ).values_list("from_resource_id", "to_resource_id", "from_resource_graph_id", "to_resource_graph_id")

            site_visit_ids = set()
            for from_id, to_id, from_graph_id, to_graph_id in site_visit_relationships:
                if str(from_graph_id) == self._site_visit_graph_id:
                    site_visit_ids.add(from_id)
                if str(to_graph_id) == self._site_visit_graph_id:
                    site_visit_ids.add(to_id)

            if site_visit_ids:
                site_visit_ids_list = list(site_visit_ids)

                parent_relationships = ResourceXResource.objects.filter(
                    Q(from_resource_id__in=site_visit_ids_list, to_resource_graph_id=parent_graph_id) |
                    Q(to_resource_id__in=site_visit_ids_list, from_resource_graph_id=parent_graph_id)
                ).values_list("from_resource_id", "to_resource_id", "from_resource_graph_id")

                for from_id, to_id, from_graph_id in parent_relationships:
                    if str(from_graph_id) == parent_graph_id:
                        parent_ids.add(str(from_id))
                    else:
                        parent_ids.add(str(to_id))

        return parent_ids

    def _get_resource_ids_for_section(
        self,
        section_data: dict,
        datatype_factory: DataTypeFactory,
        se: any,
    ) -> set:
        graph_id = section_data.get("graph_id")

        if not graph_id:
            return set()

        section_query = self._build_section_query(section_data, datatype_factory)

        has_filters = (
            section_query.dsl["bool"]["must"]
            or section_query.dsl["bool"]["should"]
        )

        if not has_filters:
            return set()

        full_query = Bool()
        full_query.filter(Terms(field="graph_id", terms=[graph_id]))
        full_query.must(section_query)

        resource_ids = set()

        results = se.search(
            index=RESOURCES_INDEX,
            query=full_query.dsl,
            size=10000,
            scroll="2m",
            _source=False,
        )

        scroll_id = results.get("_scroll_id")
        hits = results.get("hits", {}).get("hits", [])

        for hit in hits:
            resource_ids.add(hit["_id"])

        while len(hits) > 0:
            results = se.es.scroll(scroll_id=scroll_id, scroll="2m")
            scroll_id = results.get("_scroll_id")
            hits = results.get("hits", {}).get("hits", [])

            for hit in hits:
                resource_ids.add(hit["_id"])

        if scroll_id:
            se.es.clear_scroll(scroll_id=scroll_id)

        return resource_ids

    def _parse_query_data(self, querystring_params: Any) -> dict:
        if not querystring_params:
            return {}

        if isinstance(querystring_params, str):
            return JSONDeserializer().deserialize(querystring_params)

        return querystring_params

    def _update_pagination(self, response_object: dict, total: int, page: int) -> None:
        paginator, pages = get_paginator(
            self.request,
            response_object["results"],
            total,
            page,
            settings.SEARCH_ITEMS_PER_PAGE,
        )

        page_obj = paginator.page(page)

        pagination_data = {
            "current_page": page_obj.number,
            "end_index": page_obj.end_index(),
            "has_next": page_obj.has_next(),
            "has_other_pages": page_obj.has_other_pages(),
            "has_previous": page_obj.has_previous(),
            "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
            "pages": pages,
            "previous_page_number": page_obj.previous_page_number() if page_obj.has_previous() else None,
            "start_index": page_obj.start_index(),
        }

        if "paging-filter" not in response_object:
            response_object["paging-filter"] = {}

        response_object["paging-filter"]["paginator"] = pagination_data

    def append_dsl(self, search_query_object: dict, **kwargs: Any) -> None:
        querystring_params = kwargs.get("querystring", "{}")
        raw_data = self._parse_query_data(querystring_params)

        self._query_data = raw_data

        if not raw_data:
            return

        translate_mode = raw_data.get("translate_mode", "none")
        sections = raw_data.get("sections", [])

        if not sections:
            return

        if translate_mode == "intersection":
            return

        datatype_factory = DataTypeFactory()
        cross_model_query = Bool()

        for section_data in sections:
            graph_id = section_data.get("graph_id")

            if not graph_id:
                continue

            section_query = self._build_section_query(section_data, datatype_factory)

            has_filters = (
                section_query.dsl["bool"]["must"]
                or section_query.dsl["bool"]["should"]
            )

            if not has_filters:
                continue

            graph_with_filter = Bool()
            graph_with_filter.filter(Terms(field="graph_id", terms=[graph_id]))
            graph_with_filter.must(section_query)

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
        raw_data = self._query_data

        if not raw_data:
            return

        translate_mode = raw_data.get("translate_mode", "none")
        sections = raw_data.get("sections", [])

        if translate_mode != "intersection":
            return

        if not sections:
            return

        page, per_page, start = self._get_pagination_params()
        cache_key = self._get_cache_key(raw_data)
        cached_ids = cache.get(cache_key)

        if cached_ids is not None:
            combined_parent_ids = set(cached_ids)
        else:
            parent_graph_slug = GraphSlugs.ARCHAEOLOGICAL_SITE
            parent_graph = GraphModel.objects.filter(slug=parent_graph_slug).only("graphid").first()
            parent_graph_id = str(parent_graph.graphid) if parent_graph else None

            datatype_factory = DataTypeFactory()
            se = SearchEngineFactory().create()
            combined_parent_ids = None

            for section_data in sections:
                graph_id = section_data.get("graph_id")

                resource_ids = self._get_resource_ids_for_section(section_data, datatype_factory, se)

                if not resource_ids:
                    combined_parent_ids = set()
                    break

                parent_ids = self._get_parent_ids_for_resources(
                    resource_ids,
                    graph_id,
                    parent_graph_id,
                )

                if combined_parent_ids is None:
                    combined_parent_ids = parent_ids
                else:
                    combined_parent_ids = combined_parent_ids.intersection(parent_ids)

            if combined_parent_ids is None:
                combined_parent_ids = set()

            cache.set(cache_key, list(combined_parent_ids), CACHE_TIMEOUT)

        if not combined_parent_ids:
            response_object["results"]["hits"]["hits"] = []
            response_object["results"]["hits"]["total"]["value"] = 0
            response_object["total_results"] = 0
            self._update_pagination(response_object, 0, 1)
            return

        total_results = len(combined_parent_ids)
        parent_ids_list = sorted(list(combined_parent_ids))
        paginated_ids = parent_ids_list[start:start + per_page]

        if not paginated_ids:
            response_object["results"]["hits"]["hits"] = []
            response_object["results"]["hits"]["total"]["value"] = total_results
            response_object["total_results"] = total_results
            self._update_pagination(response_object, total_results, page)
            return

        se = SearchEngineFactory().create()
        parent_query = Bool()
        parent_query.filter(Terms(field="resourceinstanceid", terms=paginated_ids))

        parent_results = se.search(
            index=RESOURCES_INDEX,
            query=parent_query.dsl,
            size=per_page,
        )

        parent_hits = parent_results.get("hits", {}).get("hits", [])

        for hit in parent_hits:
            source = hit.get("_source", {})
            displayname = source.get("displayname")

            if isinstance(displayname, list) and displayname:
                source["displayname"] = displayname[0].get("value", "")

            displaydescription = source.get("displaydescription")

            if isinstance(displaydescription, list) and displaydescription:
                source["displaydescription"] = displaydescription[0].get("value", "")

        self._add_permission_properties(parent_hits)

        response_object["results"]["hits"]["hits"] = parent_hits
        response_object["results"]["hits"]["total"] = {
            "relation": "eq",
            "value": total_results,
        }
        response_object["total_results"] = total_results

        self._update_pagination(response_object, total_results, page)

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
