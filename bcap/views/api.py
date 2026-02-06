import json
from traceback import print_exception

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from arches.app.views.api import APIBase, MVT as MVTBase
import logging
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import JSONParser
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import JSONParser
from rest_framework.settings import api_settings
from arches.app.models import models
from arches.app.models.models import GraphModel, ResourceInstance, ResourceXResource
from django.core.exceptions import FieldError

from arches import VERSION as arches_version

from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer
from bcap.util.borden_number_api import BordenNumberApi, MissingGeometryError
from bcap.util.business_data_proxy import LegislativeActDataProxy
from arches.app.models import models
from bcap.util.mvt_tiler import MVTTiler
from arches.app.models.system_settings import settings
from arches.app.search.components.base import SearchFilterFactory
from arches.app.search.mappings import RESOURCES_INDEX
from arches.app.search.search_engine_factory import SearchEngineInstance

from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ReadOnly, ResourceEditor
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin
from arches_controlled_lists.models import ListItem, ListItemValue
from oauth2_provider.views.generic import ProtectedResourceView
import re

logger = logging.getLogger(__name__)


class BordenNumberBase:
    api = BordenNumberApi()

    # Generate a new borden number and return it -- NB - this doesn't reserve it at this point
    def _get_impl(self, request, resourceinstanceid=None):
        try:
            new_borden_number = self.api.get_next_borden_number(
                resourceinstanceid=resourceinstanceid
            )
            # print("Got borden grid: %s" % borden_grid)
            return_data = (
                '{"status": "success", "borden_number": "%s"}' % new_borden_number
            )
        except MissingGeometryError as e:
            return_data = '{"status": "error", "message": "%s"}' % str(e)
        except Exception as e:
            logger.error(f"Unable to generate borden number: %s", e)
            print_exception(e)
            return_data = '{"status": "error", "message": "An unexpected error occurred. Please contact system support."}'
        return_bytes = return_data.encode("utf-8")
        return HttpResponse(return_bytes, content_type="application/json")

    # Reserve a borden number for BCRHP. Borden numbers are automatically reserved for BCAP
    # by way of saving the card with a new borden number.
    def _post_impl(self, request):
        geometry_str = request.POST["site_boundary"]
        geometry = json.loads(geometry_str)
        # borden_number = request.POST["borden_number"]
        reserve = (
            request.POST["reserve_borden_number"].lower()
            if "reserve_borden_number" in request.POST
            else "false"
        )

        new_borden_number = self.api.get_next_borden_number(geometry=geometry)
        if reserve == "true":
            new_borden_number = self.api.reserve_borden_number(
                re.sub("-.*", "", new_borden_number)
            )
        return_data = (
            '{"status": "success", "borden_number": "%s" }' % new_borden_number
        )
        return_bytes = return_data.encode("utf-8")
        return JSONResponse(return_bytes, content_type="application/json")


@method_decorator(csrf_exempt, name="dispatch")
class BordenNumber(APIBase, BordenNumberBase):
    """
    Existing internal endpoint – unchanged semantics.
    """

    def get(self, request, resourceinstanceid=None):
        return self._get_impl(request, resourceinstanceid)


@method_decorator(csrf_exempt, name="dispatch")
class BordenNumberExternal(ProtectedResourceView, BordenNumberBase):

    def post(self, request, *args, **kwargs):
        return self._post_impl(request)


class ControlledListHierarchy(APIBase):
    def get(self, request, list_item_id):
        try:
            item = ListItem.objects.get(id=list_item_id)
            labels = []

            while item:
                label = (
                    ListItemValue.objects.filter(
                        list_item=item,
                        valuetype_id="prefLabel",
                    )
                    .values_list("value", flat=True)
                    .first()
                )

                if label:
                    labels.append(label)

                item = item.parent

            labels.reverse()

            return JSONResponse({"labels": labels})
        except ListItem.DoesNotExist:
            return JSONResponse({"labels": []})


class LegislativeAct(APIBase):
    def get(self, request, act_id):
        legislative_act_proxy = LegislativeActDataProxy()
        act = legislative_act_proxy.get_authorities(act_id)
        # print("Scientific Names: %s" % names)
        return JSONResponse(JSONSerializer().serializeToPython(act))


class MVT(MVTBase):
    def get(self, request, nodeid, zoom, x, y):
        if hasattr(request.user, "userprofile") is not True:
            models.UserProfile.objects.create(user=request.user)

        viewable_nodegroups = request.user.userprofile.viewable_nodegroups
        user = request.user

        tile = MVTTiler().createTile(nodeid, viewable_nodegroups, user, zoom, x, y)

        if not tile or not len(tile):
            raise Http404()

        return HttpResponse(tile, content_type="application/x-protobuf")


class ArchesSiteVisitSerializer(ArchesResourceSerializer):
    class Meta(ArchesResourceSerializer.Meta):
        graph_slug = "site_visit"


class RelatedSiteVisits(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [ResourceEditor | ReadOnly]
    serializer_class = ArchesResourceSerializer
    parser_classes = [JSONParser, MultiPartJSONParser]
    pagination_class = ArchesLimitOffsetPagination

    def get_queryset(self):
        options = self.serializer_class.Meta
        resource_ids_string = [str(uuid) for uuid in self.resource_ids]

        try:
            if issubclass(options.model, ResourceInstance):
                qs = options.model.get_tiles(
                    self.graph_slug,
                    as_representation=True,
                ).select_related("graph")

                qs = (
                    qs.filter(parent_site__id__in=resource_ids_string)
                    if self.graph_slug == "archaeological_site"
                    else qs.filter(archaeological_site__id__in=resource_ids_string)
                )

                if arches_version >= (8, 0):
                    qs = qs.select_related("resource_instance_lifecycle_state")
            else:  # pragma: no cover
                raise NotImplementedError
            # print(f"Related Site Visits Queryset: {qs}")
            print(f"Returning related resources: {self.graph_slug}")
            return qs
        except FieldError:
            msg = (
                _("Field archaeological_site not found in graph: %s") % self.graph_slug
            )
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: msg})
        except ValueError:
            msg = _("No nodes found for graph slug: %s") % self.graph_slug
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: msg})


class ResourceGraphs(APIBase):
    def get(self, request):
        from arches.app.models.system_settings import settings

        graphs = (
            models.GraphModel.objects.filter(isresource=True, is_active=True)
            .exclude(pk=settings.SYSTEM_SETTINGS_RESOURCE_MODEL_ID)
            .exclude(source_identifier__isnull=False)
            .values("graphid", "name", "iconclass")
        )

        graph_list = []

        for graph in graphs:
            name = graph["name"]

            if isinstance(name, dict):
                name = name.get("en", list(name.values())[0] if name else "")

            graph_list.append(
                {
                    "graphid": str(graph["graphid"]),
                    "name": name,
                    "iconclass": graph["iconclass"],
                }
            )

        graph_list.sort(key=lambda x: x["name"])

        return JSONResponse({"graphs": graph_list})


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
        from arches.app.models.resource import Resource

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


class UserProfile(APIBase):
    def get(self, request):
        user_profile = models.User.objects.get(id=request.user.pk)

        group_names = [
            group.name for group in models.Group.objects.filter(user=user_profile).all()
        ]

        return JSONResponse(
            JSONSerializer().serializeToPython(
                {
                    "username": user_profile.username,
                    "first_name": user_profile.first_name,
                    "last_name": user_profile.last_name,
                    "groups": group_names,
                }
            )
        )
