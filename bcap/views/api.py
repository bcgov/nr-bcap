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
from arches.app.models.models import ResourceInstance
from django.core.exceptions import FieldError
from django.db import connection

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
                    return Response({
                        "modified_on": None,
                        "modified_by": None,
                        "error": f"Could not resolve nodegroup alias '{nodegroup_alias}'"
                    })

            if tile_id:
                modification_data = self._get_tile_modification(pk, tile_id)
            elif nodegroup_id:
                modification_data = self._get_nodegroup_modification(pk, nodegroup_id)
            else:
                modification_data = self._get_resource_modification(pk)

            return Response(modification_data)

        except Exception as e:
            return Response({
                "modified_on": None,
                "modified_by": None,
                "error": str(e)
            }, status=500)

    def _get_nodegroup_id_from_alias(self, graph: str, alias: str) -> str | None:
        with connection.cursor() as cursor:
            query = """
                SELECT DISTINCT n.nodegroupid::text
                FROM nodes n
                INNER JOIN graphs g ON n.graphid = g.graphid
                WHERE g.slug = %s
                AND n.alias = %s
                LIMIT 1
            """

            cursor.execute(
                query,
                [graph, alias]
            )

            result = cursor.fetchone()
            return result[0] if result else None

    def _get_nodegroup_modification(self, resource_id: str, nodegroup_id: str) -> dict[str, Any]:
        with connection.cursor() as cursor:
            # Find child nodegroups

            query = """
                SELECT DISTINCT t_child.nodegroupid::text
                FROM tiles t_parent
                INNER JOIN tiles t_child ON t_child.parenttileid = t_parent.tileid
                WHERE t_parent.nodegroupid = %s::uuid
                AND t_parent.resourceinstanceid = %s::uuid
            """

            cursor.execute(
                query,
                [nodegroup_id, resource_id]
            )

            child_nodegroups = [row[0] for row in cursor.fetchall()]
            all_nodegroups = [nodegroup_id, *child_nodegroups]

            # Get most recent edit from these nodegroups
            query = """
                SELECT
                    el.timestamp,
                    COALESCE(el.user_username, au.username) as username,
                    COALESCE(el.user_firstname, au.first_name) as first_name,
                    COALESCE(el.user_lastname, au.last_name) as last_name,
                    el.edittype,
                    el.transactionid,
                    el.user_email,
                    el.userid,
                    el.tileinstanceid,
                    el.nodegroupid,
                    n.alias
                FROM public.edit_log el
                LEFT JOIN public.auth_user au ON el.userid::integer = au.id
                LEFT JOIN nodes n ON el.nodegroupid::uuid = n.nodegroupid
                WHERE el.resourceinstanceid = %s
            """

            params = [resource_id]

            if len(all_nodegroups) == 1:
                query += " AND el.nodegroupid = %s"
                params.append(all_nodegroups[0])
            else:
                placeholders = ",".join(["%s"] * len(all_nodegroups))
                query += f" AND el.nodegroupid IN ({placeholders})"
                params.extend(all_nodegroups)

            query += " ORDER BY el.timestamp DESC LIMIT 1"

            cursor.execute(query, params)
            row = cursor.fetchone()

            if row:
                return self._format_response(row)

            return {
                "modified_on": None,
                "modified_by": None,
                "nodegroup_id": nodegroup_id,
                "error": "No modifications found"
            }

    def _get_tile_modification(self, resource_id: str, tile_id: str) -> dict[str, Any]:
        """Get modification info for a specific tile."""

        with connection.cursor() as cursor:
            query = """
                SELECT
                    el.timestamp,
                    COALESCE(el.user_username, au.username) as username,
                    COALESCE(el.user_firstname, au.first_name) as first_name,
                    COALESCE(el.user_lastname, au.last_name) as last_name,
                    el.edittype,
                    el.transactionid,
                    el.user_email,
                    el.userid,
                    el.tileinstanceid,
                    el.nodegroupid
                FROM public.edit_log el
                LEFT JOIN public.auth_user au ON el.userid::integer = au.id
                WHERE el.resourceinstanceid = %s
                  AND el.tileinstanceid = %s
                ORDER BY el.timestamp DESC
                LIMIT 1
            """

            cursor.execute(
                query,
                [resource_id, tile_id]
            )

            row = cursor.fetchone()

            if row:
                return self._format_response(row)

            return {
                "modified_on": None,
                "modified_by": None,
                "tile_id": tile_id,
                "error": "No modifications found for this tile"
            }

    def _get_resource_modification(self, resource_id: str) -> dict[str, Any]:
        """Get the most recent modification for the entire resource."""

        with connection.cursor() as cursor:
            query = """
                SELECT
                    el.timestamp,
                    COALESCE(el.user_username, au.username) as username,
                    COALESCE(el.user_firstname, au.first_name) as first_name,
                    COALESCE(el.user_lastname, au.last_name) as last_name,
                    el.edittype,
                    el.transactionid,
                    el.user_email,
                    el.userid,
                    el.tileinstanceid,
                    el.nodegroupid
                FROM public.edit_log el
                LEFT JOIN public.auth_user au ON el.userid::integer = au.id
                WHERE el.resourceinstanceid = %s
                ORDER BY el.timestamp DESC
                LIMIT 1
            """

            cursor.execute(
                query,
                [resource_id]
            )

            row = cursor.fetchone()

            if row:
                return self._format_response(row)

            return {
                "modified_on": None,
                "modified_by": None,
                "error": "No modifications found"
            }

    def _format_response(self, row) -> dict[str, Any]:
        """Format response with user name handling."""

        timestamp = row[0]
        username = row[1]
        first_name = row[2]
        last_name = row[3]
        edit_type = row[4]
        transaction_id = row[5] if len(row) > 5 else None
        user_email = row[6] if len(row) > 6 else None
        tile_id = row[8] if len(row) > 8 else None
        nodegroup_id = row[9] if len(row) > 9 else None
        nodegroup_alias = row[10] if len(row) > 10 else None

        if first_name and last_name:
            display_name = f"{first_name} {last_name}"
        elif username:
            display_name = username
        elif first_name:
            display_name = first_name
        else:
            display_name = self._get_system_user_name(edit_type)

        result = {
            "modified_on": timestamp.isoformat() if timestamp else None,
            "modified_by": display_name,
            "transaction_id": str(transaction_id) if transaction_id else None,
            "edit_type": edit_type,
            "user_email": user_email,
            "is_system_edit": not bool(username or first_name or last_name)
        }

        if tile_id:
            result["tile_id"] = str(tile_id)

        if nodegroup_id:
            result["nodegroup_id"] = str(nodegroup_id)

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
