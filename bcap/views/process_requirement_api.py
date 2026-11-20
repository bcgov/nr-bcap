"""Process Requirement API that widens the generated owner-scoped routes:
superusers and Resource Editors may read any instance, while everyone else stays
scoped to the resources they created.

Overrides the generated routes (see bcap.urls_api_documented), reusing the
generated serializer so the response shape stays in lockstep with the graph.
"""

from django.http import Http404

from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from arches.app.models.models import ResourceInstance
from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.permissions.route_guards import (
    Internal,
    SubmitterOrInternal,
    SubmitterReadsInternalReadWrites,
)
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
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.generated.process_requirement import ProcessRequirementViewMixin
from bcap.views.parsers import ValidatedMultiPartJSONParser


def _host_id_from(req_data):
    """The submission host resource ID from a serialized ProcessRequirement, or None."""
    try:
        node_value = req_data["aliased_data"]["requirement_data"]["aliased_data"][
            "submission_data"
        ]["aliased_data"]["submission_data"]["node_value"]
        return node_value[0]["resourceId"] if node_value else None
    except (KeyError, TypeError, IndexError):
        return None


def _annotate_host_graph_slugs(results):
    """Add host_graph_slug to each serialized ProcessRequirement dict in-place (one batch query)."""
    host_id_per_result = {id(r): _host_id_from(r) for r in results}
    unique_host_ids = {hid for hid in host_id_per_result.values() if hid}
    slug_by_id = {}
    if unique_host_ids:
        slug_by_id = {
            str(pk): slug
            for pk, slug in ResourceInstance.objects.filter(
                pk__in=unique_host_ids
            ).values_list("pk", "graph__slug")
        }
    for result in results:
        host_id = host_id_per_result[id(result)]
        result["host_graph_slug"] = slug_by_id.get(host_id) if host_id else None


def _require_exists(pk, slug, label):
    """404 unless a resource of the given graph exists with this pk."""
    if not ResourceTileTree.objects.filter(pk=pk, graph__slug=slug).exists():
        raise Http404(f"No {label} matches the given id.")


def _require_permit(pk):
    return _require_exists(pk, GraphSlugs.PERMIT_APPLICATION, "permit application")


def _require_permit_or_service_request(pk):
    if ResourceTileTree.objects.filter(
        pk=pk,
        graph__slug__in=[
            GraphSlugs.PERMIT_APPLICATION,
            GraphSlugs.BCAP_SERVICE_REQUEST,
        ],
    ).exists():
        return
    raise Http404("No permit application or service request matches the given id.")


def _require_requirement(pk):
    return _require_exists(pk, GraphSlugs.PROCESS_REQUIREMENT, "process requirement")


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementListView(
    ProcessRequirementViewMixin,
    ArchesModelAPIMixin,
    ListAPIView,
):
    """Collection endpoint: branch staff see every Process Requirement; an
    applicant sees the ones on the permits they or their company filed."""

    permission_classes = [SubmitterOrInternal]
    pagination_class = ArchesLimitOffsetPagination

    def get_queryset(self):
        return ProcessRequirementService.base_query(
            self.request.user, resource_ids=self.resource_ids
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        _annotate_host_graph_slugs(response.data.get("results", []))
        return response


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementView(
    ProcessRequirementViewMixin,
    ArchesModelAPIMixin,
    RetrieveUpdateDestroyAPIView,
):
    """Detail endpoint: ministry staff read and write any instance; an applicant
    may read a requirement on a permit application they can reach, and gets a 403
    on one they cannot. Writing is staff-only.

    No owner mixin: the creator filter would hide the working copies made for an
    applicant by someone else, and the queryset answers the access question anyway.
    """

    permission_classes = [SubmitterReadsInternalReadWrites]

    def get_queryset(self):
        return ProcessRequirementService.detail_query(
            self.kwargs["pk"], self.request.user
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        _annotate_host_graph_slugs([response.data])
        return response


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementSeedView(APIView):
    """POST: submit a permit module (a group of process requirements). The
    module's host resource (the child whose resource matches the permit type,
    e.g. investigation) is created from the request body and validated by its own
    serializer, the group's process requirements are cloned and attached to the
    permit, and the host submission requirement is linked to the created host.
    The created host is returned.

    The permit type is a path segment; a type with no host resource is a 400."""

    # Applicants file their own modules, so the route only asks for a login;
    # which permit they may file against is settled per request against the id
    # in the path, since that id is the only thing naming whose modules these
    # are.
    permission_classes = [SubmitterOrInternal]
    # A module carrying file uploads (a document submission and its photographs)
    parser_classes = [JSONParser, ValidatedMultiPartJSONParser]
    # Key each host's aliased_data component name off its graph, so the three
    # host types get distinct typed schemas instead of one shared, generic one.
    schema = ArchesTileAutoSchema()

    def _host_serializer_class(self, permit_type, pk):
        """The serializer for the module's host resource. 400 when the type has
        no host; 404 when the permit application or service request is unknown."""
        serializer_class = (
            MODULE_SERIALIZERS.get(permit_type) if host_graph(permit_type) else None
        )
        if serializer_class is None:
            raise ValidationError(f"Module '{permit_type}' has no host resource.")
        _require_permit_or_service_request(pk)
        return serializer_class

    @extend_schema(responses=module_host_schema(many=True))
    def get(self, request, pk, permit_type):
        """The module's host resources attached to the permit application."""
        serializer_class = self._host_serializer_class(permit_type, pk)
        hosts = ProcessRequirementService(request).permit_module_tiles(
            pk, permit_type, request.user
        )
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
        host = ProcessRequirementService(request).submit_module(
            pk, permit_type, request.user, host_serializer.save
        )
        return Response(serializer_class(host, request=request).data, status=201)


@extend_schema(tags=["External: process_requirement"])
class PermitModuleView(APIView):
    """A submitted module on a permit application, by its process_module tile id.
    DELETE drops the tile and the requirement working copies it created (grouping
    parent, child requirements, submission hosts). PATCH flips its completion
    flag, stamping or clearing the completed date without disturbing the module's
    other card nodes."""

    permission_classes = [Internal]

    @extend_schema(responses={204: None})
    def delete(self, request, pk, module_tileid):
        _require_permit(pk)
        ProcessRequirementService(request).remove_module(pk, module_tileid)
        return Response(status=204)

    @extend_schema(request=ModuleCompletionSerializer, responses={204: None})
    def patch(self, request, pk, module_tileid):
        _require_permit(pk)
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

    permission_classes = [Internal]

    def patch(self, request, requirement_id):
        _require_requirement(requirement_id)
        body = RequirementStatusSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ProcessRequirementService(request).set_requirement_status(
            requirement_id, body.validated_data.process_status
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

    permission_classes = [Internal]

    def patch(self, request, requirement_id):
        _require_requirement(requirement_id)
        body = ChecklistPatchSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        ProcessRequirementService(request).save_checklist(
            requirement_id,
            body.validated_data.name,
            body.validated_data.steps,
        )
        return Response(status=204)
