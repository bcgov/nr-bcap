"""Generic per-user draft storage: unvalidated form state for any graph as one
JSON blob, keyed by user + graph slug. The front end PUT/PATCHes `data`, GETs it
back to rehydrate on resume, then POSTs to the resource's create view to submit
(validated only then) and DELETEs the draft. Drafts are stored as resources of
the standalone 'drafts' graph via WorkflowDraftService (raw ORM, no edit log/index).

Multi-section workflows: a single resource can be composed from multiple sections
(e.g. "permit_info", "permit_scope"), each a separate draft. Related drafts share
a draft_session_id UUID. POST to create each section's draft; GET the session at
api/workflow_session/<graph_slug>/<session_id> for progress across all sections.
Only one draft may exist per (session_id, section, graph_slug) combination.

File uploads are held by reference: the front end uploads to Arches' `/temp_file`
(bytes in `files_temporary`, unattached) and keeps the `file_id` + file-list
metadata in `data`. GOTCHA: Arches won't auto-promote a TempFile's bytes into a
resource `File`, so submit must re-send the files via multipart or copy the bytes
across itself (and bcap's FILENAME_GENERATOR needs the tile to build the path)."""

from dataclasses import dataclass, field
from uuid import UUID

from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_dataclasses.serializers import DataclassSerializer

from arches.app.models.models import ResourceInstance
from arches.app.utils.permission_backend import user_can_edit_resource

from bcap.permissions.route_guards import SubmitterOrInternal
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


class WorkflowSessionSerializer(serializers.Serializer):
    """Response for a session progress query: all section drafts for one session."""

    session_id = serializers.UUIDField()
    graph_slug = serializers.CharField()
    drafts = WorkflowDraftSerializer(many=True)


@dataclass
class DraftsQuery:
    """Query params for the draft list endpoints."""

    parent: UUID | None = None
    session_id: str | None = None
    section: str | None = None


class DraftsQuerySerializer(DataclassSerializer):
    parent = serializers.UUIDField(
        required=False,
        help_text="Only drafts started from this resource.",
    )
    session_id = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="Only drafts belonging to this session.",
    )
    section = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="Only drafts for this workflow section.",
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
    # Which sub-workflow section this draft covers.
    section: str = ""
    # UUID grouping all section drafts for the same target resource creation.
    draft_session_id: str = ""


class DraftPayloadSerializer(DataclassSerializer):
    """Request body for create/update: the whole draft blob, plus the step the
    user is on and optional metadata stamped on create."""

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
    section = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=(
            "Sub-workflow section this draft covers (e.g. 'permit_info'). "
            "Immutable after create."
        ),
    )
    draft_session_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text=(
            "UUID grouping all section drafts for the same target resource. "
            "Immutable after create."
        ),
    )

    class Meta:
        dataclass = DraftPayload


class WorkflowDraftBaseView(APIView):
    # Drafts are personal scratch data, so the route itself only asks for a login
    # -- scoping in WorkflowDraftService then limits an applicant to their own,
    # while branch staff reach the drafts on the permits they review.
    permission_classes = [SubmitterOrInternal]

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
    graph_slug, so the dashboard lists them all in one round trip. Narrow with
    ?parent=<resourceinstanceid>, ?session_id=<uuid>, or ?section=<slug>."""

    @extend_schema(
        operation_id="api_workflow_draft_list_all",
        parameters=[DraftsQuerySerializer],
        responses=WorkflowDraftSerializer(many=True),
    )
    def get(self, request):
        params = DraftsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        q = params.save()
        drafts = self.store.base_query(
            request.user,
            parent_resource_id=q.parent,
            section=q.section,
            draft_session_id=q.session_id,
        )
        return Response([self.serialize(draft) for draft in drafts])


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftListCreateView(WorkflowDraftBaseView):
    """GET the current user's drafts for a graph; POST a new draft.

    Narrow the GET with ?parent=, ?session_id=, or ?section=. POST accepts
    section and draft_session_id to create a section-scoped draft within a
    multi-section workflow. Only one draft per (session_id, section) is allowed;
    a 409 is returned if one already exists."""

    @extend_schema(
        parameters=[DraftsQuerySerializer],
        responses=WorkflowDraftSerializer(many=True),
    )
    def get(self, request, graph_slug):
        params = DraftsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        q = params.save()
        drafts = self.store.base_query(
            request.user,
            graph_slug,
            parent_resource_id=q.parent,
            section=q.section,
            draft_session_id=q.session_id,
        )
        return Response([self.serialize(draft) for draft in drafts])

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def post(self, request, graph_slug):
        body = self.payload(request)
        self.verify_parent_resource_access(body.parent_resource_id)

        # Reject duplicate section within a session: one draft per section per session.
        if body.section and body.draft_session_id:
            existing = self.store.base_query(
                request.user,
                graph_slug,
                section=body.section,
                draft_session_id=body.draft_session_id,
            ).first()
            if existing:
                return Response(
                    {
                        "detail": (
                            "A draft for this section already exists in this session."
                        ),
                        "existing_id": str(existing.pk),
                    },
                    status=409,
                )

        graph = get_current_graph(graph_slug)
        draft = self.store.create(
            request,
            graph_slug,
            body.data,
            publication_id=graph.publication_id if graph else "",
            frontend_version=body.frontend_version,
            parent_resource_id=body.parent_resource_id,
            organization_id=organization_to_stamp(request.user, body.organization_id),
            section=body.section,
            draft_session_id=body.draft_session_id,
        )
        return self.respond(draft, status=201)


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftDetailView(WorkflowDraftBaseView):
    """GET/PATCH/DELETE a single draft. PATCH shallow-merges by section key --
    untouched sections are kept, but a section present in the body is replaced
    wholesale (no deep merge), so the client sends the complete section, not just
    the fields that changed within it, and clears one by sending it empty."""

    def _get_or_404(self, request, pk):
        resource = self.store.get(request.user, pk)
        if resource is None:
            raise NotFound()
        return resource

    @extend_schema(responses=WorkflowDraftSerializer)
    def get(self, request, graph_slug, pk):
        return self.respond(self._get_or_404(request, pk))

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def patch(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        body = self.payload(request)
        merged = {**self.store.blob(resource), **body.data}
        draft = self.store.set_data(request, pk, merged, body.current_step)
        return self.respond(draft)

    @extend_schema(responses={204: None})
    def delete(self, request, graph_slug, pk):
        self._get_or_404(request, pk).delete()
        return Response(status=204)


@extend_schema(tags=["External: workflow_draft"])
class WorkflowSessionView(WorkflowDraftBaseView):
    """GET all section drafts for a workflow session. The session groups the
    drafts being built toward one target resource, keyed by session_id. The
    frontend compares drafts[].section against the workflow's expected sections
    to determine which are in-progress and which haven't been started yet."""

    @extend_schema(
        operation_id="api_workflow_session_get",
        responses=WorkflowSessionSerializer,
    )
    def get(self, request, graph_slug, session_id):
        drafts = self.store.base_query(
            request.user, graph_slug, draft_session_id=str(session_id)
        )
        serializer = WorkflowSessionSerializer(
            {
                "session_id": session_id,
                "graph_slug": graph_slug,
                "drafts": [WorkflowDraftService.record(draft) for draft in drafts],
            }
        )
        return Response(serializer.data)
