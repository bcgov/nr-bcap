from django.http import HttpResponse, Http404
from arches.app.views.api import MVT as MVTBase
import logging
from arches.app.views.api import APIBase
from rest_framework.generics import ListCreateAPIView
from rest_framework.parsers import JSONParser
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.response import Response
from arches.app.models.models import ResourceInstance, EditLog, Node
from django.core.exceptions import FieldError
from django.db.models import F
from django.contrib.auth.models import User

from arches import VERSION as arches_version

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from arches.app.utils.response import JSONResponse
from arches.app.utils.betterJSONSerializer import JSONSerializer
from bcap.util.borden_number_api import BordenNumberApi
from bcap.util.business_data_proxy import LegislativeActDataProxy
from arches.app.models import models
from bcap.util.mvt_tiler import MVTTiler
from rest_framework.views import APIView

from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ReadOnly, ResourceEditor
from arches_querysets.rest_framework.serializers import (
    ArchesResourceSerializer,
)
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin
from arches_controlled_lists.models import ListItem, ListItemValue
from typing import Any, ClassVar
from arches.app.models.models import TileModel


logger = logging.getLogger(__name__)


class ResourceEditLogView(APIView):
    """Get modification information for a resource or specific tile/nodegroup."""

    permission_classes: ClassVar = [ResourceEditor | ReadOnly]
    parser_classes: ClassVar = [JSONParser, MultiPartJSONParser]

    def get(self, request: Any, graph: str, pk: str) -> Response:
        """Get edit log information for a resource."""

        try:
            tile_id = request.GET.get("tile_id")
            nodegroup_id = request.GET.get("nodegroup_id")
            nodegroup_alias = request.GET.get("nodegroup_alias")

            if nodegroup_alias and not nodegroup_id:
                nodegroup_id = self._get_nodegroup_id_from_alias(graph, nodegroup_alias)

                if not nodegroup_id:
                    return Response(
                        {
                            "modified_on": None,
                            "modified_by": None,
                            "error": f"Could not resolve nodegroup alias '{nodegroup_alias}'",
                        }
                    )

            if tile_id:
                modification_data = self._get_tile_modification(pk, tile_id)
            elif nodegroup_id:
                modification_data = self._get_nodegroup_modification(pk, nodegroup_id)
            else:
                modification_data = self._get_resource_modification(pk)

            return Response(modification_data)

        except Exception:
            error = "Error fetching audit log information."
            logger.exception(error)

            return Response(
                {"modified_on": None, "modified_by": None, "error": error}, status=500
            )

    def _get_nodegroup_id_from_alias(self, graph: str, alias: str) -> str | None:
        try:
            node = Node.objects.filter(
                graph__slug=graph,
                alias=alias,
                pk=F('nodegroup_id')
            ).values('nodegroup_id').first()

            return str(node['nodegroup_id']) if node else None
        except Exception:
            logger.exception(f"Error resolving nodegroup alias: {alias}")
            return None

    def _get_nodegroup_modification(self, resource_id: str, nodegroup_id: str) -> dict[str, Any]:
        # Find child nodegroups
        parent_tiles = TileModel.objects.filter(
            nodegroup_id=nodegroup_id,
            resourceinstance_id=resource_id
        ).values_list('tileid', flat=True)

        # Get child tiles
        child_nodegroups = TileModel.objects.filter(
            parenttile_id__in=parent_tiles
        ).values_list('nodegroup_id', flat=True).distinct()

        # Combine parent and child nodegroups
        all_nodegroups = [nodegroup_id, *list(child_nodegroups)]

        # Get the edit log entry
        edit_log = EditLog.objects.filter(
            resourceinstanceid=resource_id,
            nodegroupid__in=all_nodegroups
        ).order_by('-timestamp').first()

        if edit_log:
            # Get nodegroup alias
            nodegroup_alias = None

            if edit_log.nodegroupid:
                node = Node.objects.filter(
                    nodegroup_id=edit_log.nodegroupid,
                    pk=F('nodegroup_id')
                ).values('alias').first()

                nodegroup_alias = node['alias'] if node else None

            return self._format_response_from_object(edit_log, nodegroup_alias)

        return {
            "modified_on": None,
            "modified_by": None,
            "nodegroup_id": nodegroup_id,
            "error": "No modifications found",
        }

    def _get_tile_modification(self, resource_id: str, tile_id: str) -> dict[str, Any]:
        """Get modification info for a specific tile using Django ORM."""

        edit_log = EditLog.objects.filter(
            resourceinstanceid=resource_id,
            tileinstanceid=tile_id
        ).order_by('-timestamp').first()

        if edit_log:
            return self._format_response_from_object(edit_log)

        return {
            "modified_on": None,
            "modified_by": None,
            "tile_id": tile_id,
            "error": "No modifications found for this tile",
        }

    def _get_resource_modification(self, resource_id: str) -> dict[str, Any]:
        """Get the most recent modification for the entire resource using Django ORM."""

        edit_log = EditLog.objects.filter(
            resourceinstanceid=resource_id
        ).order_by('-timestamp').first()

        if edit_log:
            return self._format_response_from_object(edit_log)

        return {
            "modified_on": None,
            "modified_by": None,
            "error": "No modifications found",
        }

    def _format_response_from_object(self, edit_log: EditLog, nodegroup_alias: str | None = None) -> dict[str, Any]:
        """Format response from an EditLog object."""

        username = edit_log.user_username
        first_name = edit_log.user_firstname
        last_name = edit_log.user_lastname

        if not any([username, first_name, last_name]) and edit_log.userid:
            try:
                user_id = int(edit_log.userid)
                user = User.objects.filter(id=user_id).first()

                if user:
                    username = username or user.username
                    first_name = first_name or user.first_name
                    last_name = last_name or user.last_name
            except (ValueError, TypeError):
                pass

        if first_name and last_name:
            display_name = f"{first_name} {last_name}"
        elif username:
            display_name = username
        elif first_name:
            display_name = first_name
        else:
            display_name = self._get_system_user_name(edit_log.edittype)

        result = {
            "modified_on": edit_log.timestamp.isoformat() if edit_log.timestamp else None,
            "modified_by": display_name,
            "transaction_id": str(edit_log.transactionid) if edit_log.transactionid else None,
            "edit_type": edit_log.edittype,
            "user_email": edit_log.user_email,
            "is_system_edit": not bool(username or first_name or last_name),
        }

        if edit_log.tileinstanceid:
            result["tile_id"] = str(edit_log.tileinstanceid)

        if edit_log.nodegroupid:
            result["nodegroup_id"] = str(edit_log.nodegroupid)

        if nodegroup_alias:
            result["nodegroup_alias"] = nodegroup_alias

        return result

    def _get_system_user_name(self, edit_type: str) -> str:
        """Generate appropriate system user names based on edit type."""

        if not edit_type:
            return "System User"

        edit_type_lower = edit_type.lower()

        if "import" in edit_type_lower or "etl" in edit_type_lower:
            return "Data Import"

        if "migration" in edit_type_lower:
            return "Data Migration"

        if "create" in edit_type_lower:
            return "System Import"

        return f"System ({edit_type})"


@method_decorator(csrf_exempt, name="dispatch")
class BordenNumber(APIBase):
    api = BordenNumberApi()

    # Generate a new borden number in HRIA and return it
    def get(self, request, resourceinstanceid):
        new_borden_number = self.api.get_next_borden_number(resourceinstanceid)
        # print("Got borden grid: %s" % borden_grid)
        return_data = '{"status": "success", "borden_number": "%s"}' % new_borden_number
        return_bytes = return_data.encode("utf-8")
        return HttpResponse(return_bytes, content_type="application/json")


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
