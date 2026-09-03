import json
from traceback import print_exception
from packaging.version import Version

from django.http import Http404, HttpResponse
from django.utils.decorators import method_decorator
from arches.app.views.api import APIBase, MVT as MVTBase
import logging
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import JSONParser
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt

from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from arches.app.models import models
from arches.app.models.models import ResourceInstance, ResourceXResource
from django.core.exceptions import FieldError

from arches import __version__ as arches_version

from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer

from bcap.permissions.route_permissions import Internal, internal_only_django_view
from bcap.util.bcap_aliases import GraphSlugs
from bcap.util.borden_number_api import (
    BordenGridServiceError,
    BordenNumberApi,
    MissingGeometryError,
)
from bcap.util.register_type_api import RegisterTypeApi
from bcap.util.business_data_proxy import LegislativeActDataProxy
from bcap.util.map_attributes import inject_map_attributes
from bcap.util.mvt_tiler import MVTTiler
from arches.app.models.system_settings import settings

from arches_querysets.rest_framework.generic_views import ArchesResourceDetailView
from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin
from arches_controlled_lists.models import ListItem
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
            return_data = (
                '{"status": "success", "borden_number": "%s"}' % new_borden_number
            )
        except MissingGeometryError as e:
            return_data = '{"status": "error", "message": "%s"}' % str(e)
        except BordenGridServiceError as e:
            logger.error("Borden Grid upstream service error: %s", e)
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


@internal_only_django_view
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


@internal_only_django_view
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


@internal_only_django_view
class LegislativeAct(APIBase):
    def get(self, request, act_id):
        legislative_act_proxy = LegislativeActDataProxy()
        act = legislative_act_proxy.get_authorities(act_id)
        return JSONResponse(JSONSerializer().serializeToPython(act))


class MVT(MVTBase):
    # Ungated on purpose: the tile query is scoped to the caller's readable
    # nodegroups, so an unauthenticated request gets an empty tile.
    def get(self, request, nodeid, zoom, x, y):
        if hasattr(request.user, "userprofile") is not True:
            models.UserProfile.objects.create(user=request.user)

        viewable_nodegroups = request.user.userprofile.viewable_nodegroups
        user = request.user

        tile = MVTTiler().createTile(nodeid, viewable_nodegroups, user, zoom, x, y)

        if not tile or not len(tile):
            raise Http404()

        return HttpResponse(tile, content_type="application/x-protobuf")


class RelatedSiteVisits(ArchesModelAPIMixin, ListCreateAPIView):
    permission_classes = [Internal]
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

                if self.graph_slug == GraphSlugs.ARCHAEOLOGICAL_SITE:
                    qs = qs.filter(parent_site__id__in=resource_ids_string)
                elif self.graph_slug == GraphSlugs.PUBLICATION:
                    publication_ids = (
                        ResourceXResource.objects.filter(
                            from_resource_id__in=resource_ids_string
                        )
                        .values("to_resource_id")
                        .all()
                    )
                    qs = qs.filter(
                        resourceinstanceid__in=publication_ids
                    ).select_related("graph")
                else:
                    qs = qs.filter(archaeological_site__id__in=resource_ids_string)

                if Version(arches_version) >= Version("8.0"):
                    qs = qs.select_related("resource_instance_lifecycle_state")
            else:  # pragma: no cover
                raise NotImplementedError
            return qs
        except FieldError:
            msg = (
                _("Field archaeological_site not found in graph: %s") % self.graph_slug
            )
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: msg})
        except ValueError:
            msg = _("No nodes found for graph slug: %s") % self.graph_slug
            raise ValidationError({api_settings.NON_FIELD_ERRORS_KEY: msg})


@internal_only_django_view
class RegisterType(APIBase):
    api = RegisterTypeApi()

    def get(self, request, resourceinstanceid=None):
        try:
            result = self.api.calculate(str(resourceinstanceid))
            data = json.dumps(result)
        except Exception:
            logger.exception("Unable to calculate register type")
            data = json.dumps(
                {
                    "status": "error",
                    "message": "An unexpected error occurred. Please contact system support.",
                }
            )
        return HttpResponse(data.encode("utf-8"), content_type="application/json")


class BCAPResourceDetailView(ArchesResourceDetailView):
    """Standard arches_querysets resource detail. For graphs declared in
    map_attributes.GRAPH_CONFIG we inject the configured attributes into
    the geojson FeatureCollection node's per-feature properties so the
    map can drive styling from them without a second fetch.

    No gate of its own: the base view checks each instance through the
    permission framework (read to GET, edit to PATCH), which applies the graph
    policy per resource.
    """

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        inject_map_attributes(response.data, kwargs["pk"], kwargs.get("graph"))
        return response
