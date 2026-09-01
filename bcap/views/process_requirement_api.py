"""Process Requirement API that widens the generated owner-scoped routes:
superusers and Resource Editors may read any instance, while everyone else stays
scoped to the resources they created.

Overrides the generated routes (see bcap.urls_api_documented), reusing the
generated serializer so the response shape stays in lockstep with the graph.
"""

from django.http import Http404

from drf_spectacular.utils import extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from arches.app.models.resource import Resource

from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.multipart_json_parser import MultiPartJSONParser
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from arches_zod_validation.views.mixins import UserOwnedResourceMixin

from bcap.permissions.groups import is_internal_user
from bcap.permissions.route_permissions import Internal, SubmitterOrInternal
from bcap.serializers.graph_serializers import MODULE_SERIALIZERS, module_host_schema
from bcap.serializers.process_requirement_serializers import (
    AddRequirementSerializer,
    ChecklistPatchSerializer,
    ModuleCompletionSerializer,
    ReorderRequirementsSerializer,
    RequirementAssigneeSerializer,
    RequirementStatusSerializer,
)
from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.schema import ArchesTileAutoSchema
from bcap.services.process_requirement.template_specs import host_graph
from bcap.util.indexing import bulk_index
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.generated.process_requirement import ProcessRequirementViewMixin


def _require_exists(pk, slug, msg):
    """404 unless a resource of the given graph exists with this pk."""
    if not ResourceTileTree.objects.filter(pk=pk, graph__slug=slug).exists():
        raise Http404(msg)


class StaffReadsAnyMixin(UserOwnedResourceMixin):
    """Owner-scope the queryset like the base mixin, but let staff read any
    instance -- they review every requirement, not only the ones they made."""

    def get_queryset(self):
        if is_internal_user(self.request.user):
            # Skip the owner filter; fall through to the full graph queryset.
            return super(UserOwnedResourceMixin, self).get_queryset()
        return super().get_queryset()


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementListView(
    ProcessRequirementViewMixin,
    StaffReadsAnyMixin,
    ArchesModelAPIMixin,
    ListAPIView,
):
    """Collection endpoint: superusers and Resource Editors see every Process
    Requirement; other users see only the ones they created."""

    permission_classes = [SubmitterOrInternal]
    pagination_class = ArchesLimitOffsetPagination


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementView(
    ProcessRequirementViewMixin,
    StaffReadsAnyMixin,
    ArchesModelAPIMixin,
    RetrieveUpdateDestroyAPIView,
):
    """Detail endpoint: superusers and Resource Editors may read any instance;
    other users requesting one they don't own get a 404."""

    permission_classes = [SubmitterOrInternal]


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementSeedView(APIView):
    """POST: submit a permit module (a group of process requirements). The
    module's host resource (the child whose resource matches the permit type,
    e.g. investigation) is created from the request body and validated by its own
    serializer, the group's process requirements are cloned and attached to the
    permit, and the host submission requirement is linked to the created host.
    The created host is returned.

    The permit type is a path segment; a type with no host resource is a 400."""

    authentication_classes = [SessionAuthentication]
    # Applicants file their own modules, so this only asks for a login; which
    # permits they may file against is settled by the permit lookup.
    permission_classes = [SubmitterOrInternal]
    # A module carrying file uploads (a document submission and its photographs)
    parser_classes = [JSONParser, MultiPartJSONParser]
    # Key each host's aliased_data component name off its graph, so the three
    # host types get distinct typed schemas instead of one shared, generic one.
    schema = ArchesTileAutoSchema()

    def _host_serializer_class(self, permit_type, pk):
        """The serializer for the module's host resource. 400 when the type has
        no host; 404 when the permit application is unknown."""
        serializer_class = (
            MODULE_SERIALIZERS.get(permit_type) if host_graph(permit_type) else None
        )
        if serializer_class is None:
            raise ValidationError(f"Module '{permit_type}' has no host resource.")
        _require_exists(
            pk,
            GraphSlugs.PERMIT_APPLICATION,
            "No permit application matches the given id.",
        )
        return serializer_class

    @extend_schema(responses=module_host_schema(many=True))
    def get(self, request, pk, permit_type):
        """The module's host resources attached to the permit application."""
        serializer_class = self._host_serializer_class(permit_type, pk)
        hosts = ProcessRequirementService(request).permit_module_tiles(pk, permit_type)
        return Response(
            [serializer_class(host, request=request).data for host in hosts]
        )

    @extend_schema(
        request=module_host_schema(many=False),
        responses=module_host_schema(many=False),
    )
    def post(self, request, pk, permit_type):
        serializer_class = self._host_serializer_class(permit_type, pk)
        host_serializer = serializer_class(data=request.data, request=request)
        host_serializer.is_valid(raise_exception=True)
        host = host_serializer.save()
        host_resource = Resource.objects.get(pk=host.pk)
        host_resource.save_descriptors()
        ProcessRequirementService(request).attach_requirements(pk, permit_type, host)
        bulk_index([host_resource])
        # Re-read the saved host as representation so the response carries
        # display_value (what the review screen renders).
        fresh = ResourceTileTree.get_tiles(
            host_graph(permit_type), resource_ids=[host.pk], as_representation=True
        ).get()
        return Response(serializer_class(fresh, request=request).data, status=201)


@extend_schema(tags=["External: process_requirement"])
class PermitModuleView(APIView):
    """A submitted module on a permit application, by its process_module tile id.
    DELETE drops the tile and the requirement working copies it created (grouping
    parent, child requirements, submission hosts). PATCH flips its completion
    flag, stamping or clearing the completed date without disturbing the module's
    other card nodes."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [Internal]

    @extend_schema(responses={204: None})
    def delete(self, request, pk, module_tileid):
        _require_exists(
            pk,
            GraphSlugs.PERMIT_APPLICATION,
            "No permit application matches the given id.",
        )
        ProcessRequirementService(request).remove_module(pk, module_tileid)
        return Response(status=204)

    @extend_schema(request=ModuleCompletionSerializer, responses={204: None})
    def patch(self, request, pk, module_tileid):
        _require_exists(
            pk,
            GraphSlugs.PERMIT_APPLICATION,
            "No permit application matches the given id.",
        )
        body = ModuleCompletionSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        found = ProcessRequirementService(request).set_module_completed(
            pk, module_tileid, body.validated_data.completed
        )
        if not found:
            raise Http404("No module matches the given tile id.")
        return Response(status=204)


@extend_schema(tags=["Internal: process_requirement"])
class ModuleRequirementsView(APIView):
    """A module's process requirements: PATCH reorders them (an order list of
    resource ids), POST adds a blank one.

    Reorder is its own endpoint, not the generic permit PATCH, so the client sends
    just the id order rather than rebuilding and resending the whole module tree to
    keep a partial write from deleting the omitted tiles."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [Internal]

    @extend_schema(request=ReorderRequirementsSerializer, responses={204: None})
    def patch(self, request, pk, module_tileid):
        body = ReorderRequirementsSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ProcessRequirementService(request).reorder_requirements(
            pk, module_tileid, body.validated_data.order
        )
        return Response(status=204)

    @extend_schema(request=AddRequirementSerializer, responses={201: None})
    def post(self, request, pk, module_tileid):
        body = AddRequirementSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        name = body.validated_data.name or "New requirement"
        ProcessRequirementService(request).add_blank_requirement(
            pk, module_tileid, name
        )
        return Response(status=201)


@extend_schema(tags=["Internal: process_requirement"], responses={204: None})
class ModuleRequirementView(APIView):
    """DELETE: remove one process requirement from a module by its resource id
    (the child tile, the requirement resource, and its submission host).
    PATCH: set or clear its ministry assignee."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [Internal]

    def delete(self, request, pk, module_tileid, requirement_id):
        ProcessRequirementService(request).remove_requirement(
            pk, module_tileid, requirement_id
        )
        return Response(status=204)

    @extend_schema(request=RequirementAssigneeSerializer)
    def patch(self, request, pk, module_tileid, requirement_id):
        body = RequirementAssigneeSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        found = ProcessRequirementService(request).set_ministry_assignee(
            pk, module_tileid, requirement_id, body.validated_data.contributor_id
        )
        if not found:
            raise Http404("No requirement matches the given id on this module.")
        return Response(status=204)


@extend_schema(
    tags=["Internal: process_requirement"],
    request=RequirementStatusSerializer,
    responses={204: None},
)
class RequirementStatusView(APIView):
    """PATCH: mark a process requirement satisfied/unsatisfied on its assessment
    tile. For non-checklist requirements, whose status is set directly rather
    than derived from subrequirements."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [Internal]

    def patch(self, request, requirement_id):
        _require_exists(
            requirement_id,
            GraphSlugs.PROCESS_REQUIREMENT,
            "No process requirement matches the given id.",
        )
        body = RequirementStatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ProcessRequirementService(request).set_requirement_status(
            requirement_id, body.validated_data.satisfied
        )
        return Response(status=204)


@extend_schema(
    tags=["Internal: process_requirement"],
    request=ChecklistPatchSerializer,
    responses={204: None},
)
class RequirementChecklistView(APIView):
    """PATCH: save a process requirement's checklist, its name and full ordered
    step list, reconciled server-side against the sent list. A step is
    {tileid?, name, description}; omit tileid to create one, and a persisted step
    left out of the list is deleted."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [Internal]

    def patch(self, request, requirement_id):
        _require_exists(
            requirement_id,
            GraphSlugs.PROCESS_REQUIREMENT,
            "No process requirement matches the given id.",
        )
        body = ChecklistPatchSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ProcessRequirementService(request).save_checklist(
            requirement_id,
            body.validated_data.name,
            body.validated_data.steps,
        )
        return Response(status=204)
