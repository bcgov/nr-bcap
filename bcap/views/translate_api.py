"""Translate-to-resource-type: list the resource types a search can be
translated into, and map a set of source resources onto their related resources
of a target type. Both are internal search tooling."""

import json

from django.http import HttpRequest, JsonResponse
from django.views import View

from arches.app.models.models import GraphModel, ResourceInstance, ResourceXResource
from arches.app.models.resource import Resource
from arches.app.models.system_settings import settings
from arches.app.search.components.base import SearchFilterFactory
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineInstance

from bcap.permissions.route_permissions import internal_only_django_view


@internal_only_django_view
class TranslatableResourceTypesView(View):
    def get(self, request):
        resource_types = []

        graphs = (
            GraphModel.objects.filter(isresource=True, is_active=True)
            .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(source_identifier__isnull=False)
            .values("graphid", "name", "iconclass")
        )

        for graph in graphs:
            name = graph["name"]
            if isinstance(name, dict):
                name = name.get("en", list(name.values())[0] if name else "")
            else:
                name = str(name)

            resource_types.append(
                {
                    "graphid": str(graph["graphid"]),
                    "name": name,
                    "iconclass": graph["iconclass"] or "fa fa-question",
                }
            )

        resource_types.sort(key=lambda x: x["name"])

        return JsonResponse({"status": "success", "resource_types": resource_types})


@internal_only_django_view
class TranslateToResourceTypeView(View):
    def _create_search_request(self, request: HttpRequest) -> HttpRequest:
        from django.http import QueryDict

        search_request = HttpRequest()
        search_request.method = "GET"
        search_request.user = request.user
        search_request.session = request.session

        get_params = QueryDict(mutable=True)
        get_params["paging-filter"] = "1"

        excluded_keys = {
            "paging-filter",
            "target_graph_id",
            "source_ids",
            "csrfmiddlewaretoken",
        }

        for key, value in request.POST.items():
            if key not in excluded_keys and value:
                get_params[key] = value

        search_request.GET = get_params

        return search_request

    def _get_all_resource_ids_from_search(self, request: HttpRequest) -> tuple:
        search_request = self._create_search_request(request)
        search_filter_factory = SearchFilterFactory(search_request)
        searchview_instance = search_filter_factory.get_searchview_instance()

        if not searchview_instance:
            return [], 0

        response_object, search_query_object = (
            searchview_instance.handle_search_results_query(
                search_filter_factory, returnDsl=True
            )
        )

        query = search_query_object["query"].dsl
        query.pop("_source_excludes", None)
        query.pop("_source_includes", None)
        query.pop("source_excludes", None)
        query.pop("source_includes", None)
        query.pop("from", None)

        query["_source"] = False
        query["size"] = 0
        query["track_total_hits"] = True

        count_results = SearchEngineInstance.search(index=RESOURCES_INDEX, body=query)
        total_count = count_results.get("hits", {}).get("total", {}).get("value", 0)

        query["size"] = 500

        resource_ids = []
        batch_from = 0
        max_results = 10000

        while batch_from < max_results:
            query["from"] = batch_from

            results = SearchEngineInstance.search(index=RESOURCES_INDEX, body=query)

            if not results:
                break

            hits = results.get("hits", {}).get("hits", [])

            if not hits:
                break

            for hit in hits:
                resource_ids.append(hit["_id"])

            if len(hits) < 500:
                break

            batch_from += 500

        return resource_ids, total_count

    def _get_graph_name(self, graph_id: str) -> str:
        graph = GraphModel.objects.filter(graphid=graph_id).first()

        if not graph:
            return "Unknown"

        name = graph.name

        if isinstance(name, dict):
            return name.get("en", name.get(list(name.keys())[0], "Unknown"))

        return str(name)

    def _get_related_resources_with_sources(
        self, resource_ids: list, target_graph_id: str
    ) -> dict:
        source_names = {}

        for rid in resource_ids:
            rid_str = str(rid)
            resource = Resource.objects.filter(resourceinstanceid=rid).first()

            if resource:
                name = resource.displayname()
                if name:
                    name = name.rstrip(", ").rstrip(",").strip()
                source_names[rid_str] = name if name else rid_str

        target_to_source_ids = {}

        relationships_from = ResourceXResource.objects.filter(
            from_resource_id__in=resource_ids, to_resource_graph_id=target_graph_id
        )

        for rel in relationships_from:
            target_id = str(rel.to_resource_id)
            source_id = str(rel.from_resource_id)

            if target_id not in target_to_source_ids:
                target_to_source_ids[target_id] = set()

            target_to_source_ids[target_id].add(source_id)

        relationships_to = ResourceXResource.objects.filter(
            to_resource_id__in=resource_ids, from_resource_graph_id=target_graph_id
        )

        for rel in relationships_to:
            target_id = str(rel.from_resource_id)
            source_id = str(rel.to_resource_id)

            if target_id not in target_to_source_ids:
                target_to_source_ids[target_id] = set()

            target_to_source_ids[target_id].add(source_id)

        target_to_sources = {}
        for target_id, source_id_set in target_to_source_ids.items():
            source_name_list = []
            for source_id in source_id_set:
                source_name = source_names.get(source_id, source_id)
                source_name_list.append(source_name)
            target_to_sources[target_id] = source_name_list

        return target_to_sources

    def _get_source_graph_name(self, resource_ids: list) -> str:
        if not resource_ids:
            return "Unknown"

        resource = (
            ResourceInstance.objects.filter(resourceinstanceid=resource_ids[0])
            .select_related("graph")
            .first()
        )

        if not resource or not resource.graph:
            return "Unknown"

        name = resource.graph.name

        if isinstance(name, dict):
            return name.get("en", name.get(list(name.keys())[0], "Unknown"))

        return str(name)

    def post(self, request):
        max_source_resources = settings.TRANSLATE_RESOURCE_TYPE_MAX_SOURCES

        target_graph_id = request.POST.get("target_graph_id")
        source_ids_json = request.POST.get("source_ids")

        if not target_graph_id:
            return JsonResponse(
                {"status": "error", "message": "No target resource type specified."}
            )

        if source_ids_json:
            try:
                resource_ids = json.loads(source_ids_json)
            except json.JSONDecodeError:
                return JsonResponse(
                    {"status": "error", "message": "Invalid source IDs format."}
                )

            total_count = len(resource_ids)
            source_name = self._get_source_graph_name(resource_ids)
        else:
            resource_ids, total_count = self._get_all_resource_ids_from_search(request)
            source_name = self._get_source_graph_name(resource_ids)

        if total_count > max_source_resources:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Search results exceed the {max_source_resources:,} resource limit ({total_count:,} found). Please filter your results before translating.",
                }
            )

        if not resource_ids:
            return JsonResponse(
                {"status": "error", "message": "No resources to translate."}
            )

        target_to_sources = self._get_related_resources_with_sources(
            resource_ids, target_graph_id
        )

        target_name = self._get_graph_name(target_graph_id)

        return JsonResponse(
            {
                "status": "success",
                "resource_ids": list(target_to_sources.keys()),
                "total_translated": len(target_to_sources),
                "original_count": total_count,
                "source_resource_type_name": source_name,
                "target_resource_type_name": target_name,
                "source_mapping": target_to_sources,
            }
        )
