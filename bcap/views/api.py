from traceback import print_exception

from django.http import HttpResponse, Http404
from arches.app.views.api import MVT as MVTBase
import logging
from arches.app.views.api import APIBase
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import JSONParser
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from arches.app.models.models import ResourceInstance
from django.core.exceptions import FieldError

from arches import VERSION as arches_version

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer
from bcap.util.borden_number_api import BordenNumberApi, MissingGeometryError
from bcap.util.business_data_proxy import LegislativeActDataProxy
from arches.app.models import models
from bcap.util.mvt_tiler import MVTTiler

from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ReadOnly, ResourceEditor
from arches_querysets.rest_framework.serializers import (
    ArchesResourceSerializer,
)
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin
from arches_controlled_lists.models import ListItem, ListItemValue


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class BordenNumber(APIBase):
    api = BordenNumberApi()

    # Generate a new borden number and return it -- NB - this doesn't reserve it at this point
    def get(self, request, resourceinstanceid=None):
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
    def post(self, request):
        geometry = request.POST.site_boundary
        borden_number = request.POST.borden_number
        reserve = request.POST.reserve_borden_number

        if reserve == "true":
            self.api.reserve_borden_number(geometry)
        new_borden_number = self.api.get_next_borden_number(geometry=geometry)
        return_data = '{"status": "success", borden_number: "%s" }' % new_borden_number
        return_bytes = return_data.encode("utf-8")
        return JSONResponse(return_bytes, content_type="application/json")


class LegislativeAct(APIBase):
    def get(self, request, act_id):
        legislative_act_proxy = LegislativeActDataProxy()
        act = legislative_act_proxy.get_authorities(act_id)
        # print("Scientific Names: %s" % names)
        return JSONResponse(JSONSerializer().serializeToPython(act))


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

                qs = qs.filter(archaeological_site__id__in=resource_ids_string)

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
