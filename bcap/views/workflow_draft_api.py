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

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_dataclasses.serializers import DataclassSerializer

from arches.app.models.models import ResourceInstance
from arches.app.utils.permission_backend import user_can_edit_resource

from bcap.services.workflow_draft_service import (
    DraftRecord,
    WorkflowDraftService,
)
from bcap.util.graph import get_current_graph


class WorkflowDraftSerializer(DataclassSerializer):
    graph_has_different_publication = serializers.SerializerMethodField()

    class Meta:
        dataclass = DraftRecord

    def get_graph_has_different_publication(self, obj) -> bool:
        """True when the published graph has moved on since the draft was saved."""
        if not obj.graph_publication_id:
            return False
        graph = get_current_graph(obj.graph_slug)
        return bool(graph) and str(graph.publication_id) != obj.graph_publication_id


class DraftWriteSerializer(serializers.Serializer):
    """Request body for create/update: the whole draft blob, plus an optional
    frontend version and parent resource stamped on create."""

    data = serializers.JSONField()
    frontend_version = serializers.CharField(required=False, allow_blank=True)
    parent_resource_id = serializers.CharField(required=False, allow_blank=True)


class WorkflowDraftBaseView(APIView):
    authentication_classes = [SessionAuthentication]
    # Drafts are personal scratch data -- every verb (incl. GET) owner-scoping in
    # WorkflowDraftService then limits an applicant to their own.
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


@extend_schema(tags=["External: workflow_draft"])
class WorkflowDraftListCreateView(WorkflowDraftBaseView):
    """GET the current user's drafts for a graph; POST a new draft."""

    @extend_schema(responses=WorkflowDraftSerializer(many=True))
    def get(self, request, graph_slug):
        drafts = self.store.queryset(request.user, graph_slug)
        return Response([self.serialize(self.store.to_record(d)) for d in drafts])

    @extend_schema(request=DraftWriteSerializer, responses=WorkflowDraftSerializer)
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
        return Response(self.serialize(record), status=201)


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
        return Response(self.serialize(record))

    @extend_schema(request=DraftWriteSerializer, responses=WorkflowDraftSerializer)
    def put(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        data = (request.data or {}).get("data") or {}
        return Response(self.serialize(self.store.set_data(resource, data)))

    @extend_schema(request=DraftWriteSerializer, responses=WorkflowDraftSerializer)
    def patch(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        merged = {
            **self.store.to_record(resource).data,
            **(request.data or {}).get("data", {}),
        }
        return Response(self.serialize(self.store.set_data(resource, merged)))

    @extend_schema(responses={204: None})
    def delete(self, request, graph_slug, pk):
        self._get_or_404(request, pk).delete()
        return Response(status=204)
