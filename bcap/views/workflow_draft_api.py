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
from bcap.services.workflow_draft_service import (
    DraftRecord,
    WorkflowDraftService,
)
from bcap.util.graph import get_current_graph


@extend_schema_field(aliased_data_union_schema())
class DraftDataField(serializers.JSONField):
    """The draft blob. Stored unvalidated (it is half-filled form state), so the
    field stays a passthrough at runtime and only its schema is narrowed: one
    registered graph's aliased_data, per the draft's graph_slug."""


class WorkflowDraftSerializer(DataclassSerializer):
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


class DraftsQuerySerializer(serializers.Serializer):
    """Query params for the all-graphs draft list."""

    parent = serializers.UUIDField(
        required=False,
        help_text="Only drafts started from this resource.",
    )


class DraftPayloadSerializer(serializers.Serializer):
    """Request body for create/update: the whole draft blob, plus the step the
    user is on and an optional frontend version and parent resource stamped on
    create."""

    data = DraftDataField()
    current_step = serializers.CharField(required=False, allow_blank=True)
    frontend_version = serializers.CharField(required=False, allow_blank=True)
    parent_resource_id = serializers.CharField(required=False, allow_blank=True)


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

    def serialize(self, record):
        return WorkflowDraftSerializer(record).data

    def respond(self, record, status=200):
        """A draft record as its serialized response."""
        return Response(self.serialize(record), status=status)


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
            request.user, parent_resource_id=params.validated_data.get("parent")
        )
        return Response([self.serialize(self.store.to_record(d)) for d in drafts])


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftListCreateView(WorkflowDraftBaseView):
    """GET the current user's drafts for a graph; POST a new draft."""

    @extend_schema(responses=WorkflowDraftSerializer(many=True))
    def get(self, request, graph_slug):
        drafts = self.store.queryset(request.user, graph_slug)
        return Response([self.serialize(self.store.to_record(d)) for d in drafts])

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def post(self, request, graph_slug):
        body = request.data or {}
        parent_resource_id = body.get("parent_resource_id") or ""
        self.verify_parent_resource_access(parent_resource_id)
        graph = get_current_graph(graph_slug)
        record = self.store.create(
            request.user,
            graph_slug,
            body.get("data") or {},
            publication_id=getattr(graph, "publication_id", ""),
            frontend_version=body.get("frontend_version", ""),
            parent_resource_id=parent_resource_id,
        )
        return self.respond(record, status=201)


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
        record = self.store.to_record(self._get_or_404(request, pk))
        return self.respond(record)

    def _save(self, resource, data, body):
        """Store the blob plus whatever step the body carries, serialized."""
        record = self.store.set_data(resource, data, body.get("current_step"))
        return self.respond(record)

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def put(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        body = request.data or {}
        return self._save(resource, body.get("data") or {}, body)

    @extend_schema(request=DraftPayloadSerializer, responses=WorkflowDraftSerializer)
    def patch(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        body = request.data or {}
        merged = {
            **self.store.to_record(resource).data,
            **body.get("data", {}),
        }
        return self._save(resource, merged, body)

    @extend_schema(responses={204: None})
    def delete(self, request, graph_slug, pk):
        self._get_or_404(request, pk).delete()
        return Response(status=204)
