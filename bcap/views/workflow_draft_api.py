"""Generic per-user draft storage: unvalidated form state for any graph as one
JSON blob, keyed by user + graph slug. The front end PUT/PATCHes `data`, GETs it
back to rehydrate on resume, then POSTs to the resource's create view to submit
(validated only then) and DELETEs the draft. Drafts are stored as resources of
the standalone 'drafts' graph via WorkflowDraftService (raw ORM, no edit log/index).

File uploads are held by reference: the front end uploads to Arches' `/temp_file`
(bytes in `files_temporary`, unattached) and keeps the `file_id` + file-list
metadata in `data`. GOTCHA: Arches won't auto-promote a TempFile's bytes into a
resource `File`, so submit must re-send the files via multipart or copy the bytes
across itself (and bcap's FILENAME_GENERATOR needs the tile to build the path)."""

from dataclasses import dataclass, field
from uuid import UUID

from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_dataclasses.serializers import DataclassSerializer

from arches.app.models.models import ResourceInstance
from arches.app.utils.permission_backend import user_can_edit_resource

from bcap.serializers.graph_serializers import aliased_data_union_schema
from bcap.services.workflow_draft_service import DraftRecord, WorkflowDraftService
from bcap.util.graph import get_current_graph
from bcap.views.organization_helpers import organization_to_stamp


@extend_schema_field(aliased_data_union_schema())
class DraftDataField(serializers.JSONField):
    """The draft blob. Stored unvalidated (it is half-filled form state), so the
    field stays a passthrough at runtime and only its schema is narrowed: one
    registered graph's aliased_data, per the draft's graph_slug."""


class WorkflowDraftSerializer(DataclassSerializer):
    """A saved draft: the stored form blob plus the metadata needed to resume it
    -- which graph it belongs to, the step the user left off on, when it was last
    saved, and whether that graph has been republished since."""

    data = DraftDataField()
    graph_has_different_publication = serializers.SerializerMethodField()

    class Meta:
        dataclass = DraftRecord

    def get_graph_has_different_publication(self, obj) -> bool:
        """True when the published graph has moved on since the draft was saved."""
        if not obj.graph_publication_id:
            return False
        graph = get_current_graph(obj.graph_slug)
        return bool(graph) and str(graph.publication_id) != obj.graph_publication_id


@dataclass
class DraftsQuery:
    """Query params for the all-graphs draft list."""

    parent: UUID | None = None


class DraftsQuerySerializer(DataclassSerializer):
    parent = serializers.UUIDField(
        required=False,
        help_text="Only drafts started from this resource.",
    )

    class Meta:
        dataclass = DraftsQuery


@dataclass
class DraftPayload:
    data: dict = field(default_factory=dict)
    # None when the body omits it, which leaves the stored step alone.
    current_step: str | None = None
    frontend_version: str = ""
    parent_resource_id: str = ""
    organization_id: str = ""


class DraftPayloadSerializer(DataclassSerializer):
    """Request body for create/update: the whole draft blob, plus the step the
    user is on and an optional frontend version, parent resource and owning
    organization stamped on create."""

    data = DraftDataField()
    # Blank is meaningful here: it clears the stored step, where omitting it keeps.
    current_step = serializers.CharField(required=False, allow_blank=True)
    organization_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=(
            "Organization to file the draft under, so colleagues can pick it up. "
            "Must be one the user belongs to."
        ),
    )

    class Meta:
        dataclass = DraftPayload


class WorkflowDraftBaseView(APIView):
    authentication_classes = [SessionAuthentication]
    # Drafts are personal scratch data, so the route itself only asks for a login
    # -- scoping in WorkflowDraftService then limits an applicant to their own,
    # while branch staff reach the drafts on the permits they review.
    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = WorkflowDraftService()

    def verify_parent_resource_access(self, parent_id):
        """Block linking a draft to a resource the user can't reach, or the
        draft could be surfaced against someone else's resource."""
        if not parent_id:
            return
        user = self.request.user
        if user.is_superuser:
            return
        parent = ResourceInstance.objects.filter(pk=parent_id).first()
        if parent and (
            parent.principaluser_id == user.id
            or user_can_edit_resource(user, resourceid=parent_id)
        ):
            return
        raise PermissionDenied("You do not have access to the linked resource.")

    def payload(self, request):
        """The request body as a DraftPayload, 400 on anything malformed. Partial
        so an omitted field falls back to its default rather than being required."""
        body = DraftPayloadSerializer(data=request.data or {}, partial=True)
        body.is_valid(raise_exception=True)
        return body.save()

    def serialize(self, draft):
        return WorkflowDraftSerializer(WorkflowDraftService.record(draft)).data

    def respond(self, draft, status=200):
        """A draft as its serialized response."""
        return Response(self.serialize(draft), status=status)


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftAllListView(WorkflowDraftBaseView):
    """GET the drafts the user can see, across graphs. Each carries its own
    graph_slug, so the dashboard lists them all in one round trip. Narrow to one
    permit's drafts with ?parent=<resourceinstanceid>: staff see every user's, so
    an unfiltered call hands back every draft blob in the system."""

    @extend_schema(
        operation_id="api_workflow_draft_list_all",
        parameters=[DraftsQuerySerializer],
        responses=WorkflowDraftSerializer(many=True),
    )
    def get(self, request):
        params = DraftsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        drafts = self.store.queryset(
            request.user, parent_resource_id=params.validated_data.parent
        )
        return Response([self.serialize(draft) for draft in drafts])


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftListCreateView(WorkflowDraftBaseView):
    """GET the current user's drafts for a graph; POST a new draft."""

    @extend_schema(responses=WorkflowDraftSerializer(many=True))
    def get(self, request, graph_slug):
        drafts = self.store.queryset(request.user, graph_slug)
        return Response([self.serialize(draft) for draft in drafts])

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def post(self, request, graph_slug):
        body = self.payload(request)
        self.verify_parent_resource_access(body.parent_resource_id)
        graph = get_current_graph(graph_slug)
        draft = self.store.create(
            request.user,
            graph_slug,
            body.data,
            publication_id=graph.publication_id if graph else "",
            frontend_version=body.frontend_version,
            parent_resource_id=body.parent_resource_id,
            organization_id=organization_to_stamp(request.user, body.organization_id),
        )
        return self.respond(draft, status=201)


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftDetailView(WorkflowDraftBaseView):
    """GET/PUT/PATCH/DELETE a single draft. PUT replaces the whole blob; PATCH
    shallow-merges by section key -- untouched sections are kept, but a section
    present in the body is replaced wholesale (no deep merge), so the client must
    send the complete section, not just changed fields within it."""

    def _get_or_404(self, request, pk):
        resource = self.store.get(request.user, pk)
        if resource is None:
            raise NotFound()
        return resource

    @extend_schema(responses=WorkflowDraftSerializer)
    def get(self, request, graph_slug, pk):
        return self.respond(self._get_or_404(request, pk))

    def _save(self, request, pk, data, body):
        """Store the blob plus whatever step the body carries, serialized."""
        draft = self.store.set_data(request.user, pk, data, body.current_step)
        return self.respond(draft)

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def put(self, request, graph_slug, pk):
        self._get_or_404(request, pk)
        body = self.payload(request)
        return self._save(request, pk, body.data, body)

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def patch(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        body = self.payload(request)
        merged = {**self.store.blob(resource), **body.data}
        return self._save(request, pk, merged, body)

    @extend_schema(responses={204: None})
    def delete(self, request, graph_slug, pk):
        self._get_or_404(request, pk).delete()
        return Response(status=204)
