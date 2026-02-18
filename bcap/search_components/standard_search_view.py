from datetime import datetime
import logging
from typing_extensions import Dict, Tuple

from arches.app.models.system_settings import settings
from arches.app.search.components.base import SearchFilterFactory
from arches.app.search.components.base_search_view import BaseSearchView
from arches.app.search.elasticsearch_dsl_builder import Query
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineFactory
from arches.app.utils.permission_backend import (
    user_is_resource_exporter,
    user_is_resource_reviewer,
)
from arches.app.utils.string_utils import get_str_kwarg_as_bool
from arches.app.views.search import (
    append_instance_permission_filter_dsl,
    get_permitted_nodegroups,
    get_provisional_type,
)
from django.utils.translation import gettext as _


details = {
    "classname": "StandardSearchView",
    "componentname": "standard-search-view",
    "componentpath": "views/components/search/standard-search-view",
    "config": {
        "default": True,
        "linkedSearchFilters": [
            {
                "componentname": "paging-filter",
                "executionSortorder": 2,
                "layoutSortorder": 1,
                "required": True,
                "searchcomponentid": "7aff5819-651c-4390-9b9a-a61221ba52c6",
            },
            {
                "componentname": "search-results",
                "layoutSortorder": 2,
                "searchcomponentid": "00673743-8c1c-4cc0-bd85-c073a52e03ec",
            },
            {
                "componentname": "map-filter",
                "layoutSortorder": 1,
                "searchcomponentid": "09d97fc6-8c83-4319-9cef-3aaa08c3fbec",
            },
            {
                "componentname": "cross-model-advanced-search",
                "layoutSortorder": 2,
                "searchcomponentid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            },
            {
                "componentname": "related-resources-filter",
                "layoutSortorder": 3,
                "searchcomponentid": "59f28272-d1f1-4805-af51-227771739aed",
            },
            {
                "componentname": "provisional-filter",
                "layoutSortorder": 4,
                "searchcomponentid": "073406ed-93e5-4b5b-9418-b61c26b3640f",
            },
            {
                "componentname": "resource-type-filter",
                "layoutSortorder": 5,
                "searchcomponentid": "f1c46b7d-0132-421b-b1f3-95d67f9b3980",
            },
            {
                "componentname": "lifecycle-state-filter",
                "layoutSortorder": 6,
                "searchcomponentid": "9e40969b-78c2-40b8-898b-c29265050e2f",
            },
            {
                "componentname": "saved-searches",
                "layoutSortorder": 7,
                "searchcomponentid": "6dc29637-43a1-4fba-adae-8d9956dcd3b9",
            },
            {
                "componentname": "search-export",
                "layoutSortorder": 8,
                "searchcomponentid": "9c6a5a9c-a7ec-48d2-8a25-501b55b8eff6",
            },
            {
                "componentname": "search-result-details",
                "layoutSortorder": 9,
                "searchcomponentid": "f5986dae-8b01-11ea-b65a-77903936669c",
            },
            {
                "componentname": "sort-results",
                "layoutSortorder": 10,
                "searchcomponentid": "6a2fe122-de54-4e44-8e93-b6a0cda7955c",
            },
            {
                "componentname": "term-filter",
                "layoutSortorder": 11,
                "searchcomponentid": "1f42f501-ed70-48c5-bae1-6ff7d0d187da",
            },
            {
                "componentname": "time-filter",
                "layoutSortorder": 12,
                "searchcomponentid": "7497ed4f-2085-40da-bee5-52076a48bcb1",
            },
            {
                "componentname": "paging-filter",
                "layoutSortorder": 13,
                "searchcomponentid": "7aff5819-651c-4390-9b9a-a61221ba52c6",
            },
            {
                "componentname": "search-results",
                "executionSortorder": 1,
                "layoutSortorder": 14,
                "required": True,
                "searchcomponentid": "00673743-8c1c-4cc0-bd85-c073a52e03ec",
            },
        ],
    },
    "icon": "",
    "modulename": "standard_search_view.py",
    "name": "Standard Search View",
    "searchcomponentid": "69695d63-6f03-4536-8da9-841b07116381",
    "type": "search-view",
}

logger = logging.getLogger(__name__)


class StandardSearchView(BaseSearchView):
    def append_dsl(self, search_query_object: dict, **kwargs) -> None:
        search_query_object["query"].include("displaydescription")
        search_query_object["query"].include("displayname")
        search_query_object["query"].include("geometries")
        search_query_object["query"].include("graph_id")
        search_query_object["query"].include("map_popup")
        search_query_object["query"].include("permissions")
        search_query_object["query"].include("points")
        search_query_object["query"].include("provisional_resource")
        search_query_object["query"].include("resourceinstanceid")
        search_query_object["query"].include("root_ontology_class")

        load_tiles = get_str_kwarg_as_bool("tiles", self.request.GET)
        if load_tiles:
            search_query_object["query"].include("tiles")

    def execute_query(
        self,
        search_query_object: dict,
        response_object: dict,
        **kwargs,
    ) -> None:
        for_export = get_str_kwarg_as_bool("export", self.request.GET)
        pages = self.request.GET.get("pages", None)
        total = int(self.request.GET.get("total", "0"))
        resourceinstanceid = self.request.GET.get("id", None)
        dsl = search_query_object["query"]

        if for_export or pages:
            results = dsl.search(index=RESOURCES_INDEX, scroll="1m")
            scroll_id = results["_scroll_id"]
            if not pages:
                if total <= settings.SEARCH_EXPORT_LIMIT:
                    pages = (total // settings.SEARCH_RESULT_LIMIT) + 1
                else:
                    pages = (
                        int(
                            settings.SEARCH_EXPORT_LIMIT // settings.SEARCH_RESULT_LIMIT
                        )
                        - 1
                    )
            for page in range(int(pages)):
                results_scrolled = dsl.se.es.scroll(scroll_id=scroll_id, scroll="1m")
                results["hits"]["hits"] += results_scrolled["hits"]["hits"]
        else:
            results = dsl.search(index=RESOURCES_INDEX, id=resourceinstanceid)

        if results is not None:
            if "hits" not in results:
                if "docs" in results:
                    results = {"hits": {"hits": results["docs"]}}
                else:
                    results = {"hits": {"hits": [results]}}

                results["hits"]["total"] = {"value": len(results["hits"]["hits"])}

        response_object["results"] = results

    def get_searchview_filters(self) -> list:
        search_filters = [
            available_filter
            for available_filter in self.available_search_filters
            if available_filter.componentname != "search-export"
        ]

        if user_is_resource_exporter(self.request.user):
            search_filters.extend(
                [
                    available_filter
                    for available_filter in self.available_search_filters
                    if available_filter.componentname == "search-export"
                ]
            )

        search_filters.append(self.searchview_component)

        return search_filters

    def handle_search_results_query(
        self,
        search_filter_factory: SearchFilterFactory,
        returnDsl: bool,
    ) -> Tuple[Dict, Dict]:
        se = SearchEngineFactory().create()
        search_query_object = {"query": Query(se)}
        response_object = {"results": None}
        sorted_query_obj = search_filter_factory.create_search_query_dict(
            list(self.request.GET.items()) + list(self.request.POST.items())
        )

        if sorted_query_obj.get("sort-by", ""):
            sorted_query_obj["sort-results"] = {
                "sort_by": sorted_query_obj.get("sort-by", ""),
                "sort_order": sorted_query_obj.get("sort-order", "asc"),
            }

        permitted_nodegroups = get_permitted_nodegroups(self.request.user)
        include_provisional = get_provisional_type(self.request)

        try:
            for filter_type, querystring in list(sorted_query_obj.items()):
                search_filter = search_filter_factory.get_filter(filter_type)
                if search_filter:
                    search_filter.append_dsl(
                        search_query_object,
                        permitted_nodegroups=permitted_nodegroups,
                        include_provisional=include_provisional,
                        querystring=querystring,
                    )
            append_instance_permission_filter_dsl(self.request, search_query_object)
        except Exception:
            logger.exception("Search failed")
            message = {
                "message": _("Search failed."),
            }
            raise Exception(message)

        if returnDsl:
            return response_object, search_query_object

        for filter_type, querystring in list(sorted_query_obj.items()):
            search_filter = search_filter_factory.get_filter(filter_type)
            if search_filter:
                search_filter.execute_query(search_query_object, response_object)

        if response_object["results"] is not None:
            for filter_type, querystring in list(sorted_query_obj.items()):
                search_filter = search_filter_factory.get_filter(filter_type)
                if search_filter:
                    search_filter.post_search_hook(
                        search_query_object,
                        response_object,
                        permitted_nodegroups=permitted_nodegroups,
                    )

            search_query_object.pop("query")

            for key, value in list(search_query_object.items()):
                if key not in response_object:
                    response_object[key] = value

        return response_object, search_query_object

    def post_search_hook(
        self,
        search_query_object: dict,
        response_object: dict,
        **kwargs,
    ) -> None:
        dsl = search_query_object["query"]
        response_object["reviewer"] = user_is_resource_reviewer(self.request.user)
        response_object["timestamp"] = datetime.now()
        response_object["total_results"] = dsl.count(index=RESOURCES_INDEX)
        response_object["userid"] = self.request.user.id
