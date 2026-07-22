"""Generic per-user draft storage: unvalidated form state for any graph as one
JSON blob, keyed by user + graph slug. The front end PUT/PATCHes `data`, GETs it
back to rehydrate on resume, then POSTs to the resource's create view to submit
(validated only then) and DELETEs the draft. Drafts are stored as resources of
the standalone 'drafts' graph via DraftService (raw ORM, no edit log/index).

File uploads are held by reference: the front end uploads to Arches' `/temp_file`
(bytes in `files_temporary`, unattached) and keeps the `file_id` + file-list
metadata in `data`. GOTCHA: Arches won't auto-promote a TempFile's bytes into a
resource `File`, so submit must re-send the files via multipart or copy the bytes
across itself (and bcap's FILENAME_GENERATOR needs the tile to build the path)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_dataclasses.serializers import DataclassSerializer

from arches.app.models.models import ResourceInstance
from arches.app.utils.permission_backend import user_can_edit_resource
from arches_querysets.rest_framework.permissions import ResourceEditor

from bcap.services.draft_service import DraftRecord, DraftService
from bcap.util.graph import get_current_graph

# Top-level draft key linking a draft to the resource it was started from, so
# that resource's page can list its own drafts. Not a graph alias; stripped at
# submit. The user must be able to reach the referenced resource to set it.
PARENT_RESOURCE_KEY = "parent_resource_id"


class ResourceDraftSerializer(DataclassSerializer):
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
    frontend version stamped on create."""

    data = serializers.JSONField()
    frontend_version = serializers.CharField(required=False, allow_blank=True)


class ResourceDraftBaseView(APIView):
    authentication_classes = [SessionAuthentication]
    # Drafts are personal scratch data -- every verb (incl. GET) requires the
    # editor role; owner-scoping in DraftService then limits each editor to their own.
    permission_classes = [ResourceEditor]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = DraftService()

    def verify_parent_resource_access(self, data):
        """Block linking a draft to a resource the user can't reach, or the
        draft could be surfaced against someone else's resource."""
        parent_id = (data or {}).get(PARENT_RESOURCE_KEY)
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
        return ResourceDraftSerializer(record).data


@extend_schema(tags=["External: resource_draft"])
class ResourceDraftListCreateView(ResourceDraftBaseView):
    """GET the current user's drafts for a graph; POST a new draft."""

    @extend_schema(responses=ResourceDraftSerializer(many=True))
    def get(self, request, graph_slug):
        drafts = self.store.queryset(request.user, graph_slug)
        return Response([self.serialize(self.store.to_record(d)) for d in drafts])

    @extend_schema(request=DraftWriteSerializer, responses=ResourceDraftSerializer)
    def post(self, request, graph_slug):
        data = (request.data or {}).get("data") or {}
        self.verify_parent_resource_access(data)
        graph = get_current_graph(graph_slug)
        record = self.store.create(
            request.user,
            graph_slug,
            data,
            publication_id=getattr(graph, "publication_id", ""),
            frontend_version=(request.data or {}).get("frontend_version", ""),
        )
        return Response(self.serialize(record), status=201)


@extend_schema(tags=["External: resource_draft"])
class ResourceDraftDetailView(ResourceDraftBaseView):
    """GET/PUT/PATCH/DELETE a single draft. PUT replaces the whole blob; PATCH
    shallow-merges by section key -- untouched sections are kept, but a section
    present in the body is replaced wholesale (no deep merge), so the client must
    send the complete section, not just changed fields within it."""

    def _get_or_404(self, request, pk):
        resource = self.store.get(request.user, pk)
        if resource is None:
            raise NotFound()
        return resource

    @extend_schema(responses=ResourceDraftSerializer)
    def get(self, request, graph_slug, pk):
        record = self.store.to_record(self._get_or_404(request, pk))
        return Response(self.serialize(record))

    @extend_schema(request=DraftWriteSerializer, responses=ResourceDraftSerializer)
    def put(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        data = (request.data or {}).get("data") or {}
        self.verify_parent_resource_access(data)
        return Response(self.serialize(self.store.set_data(resource, data)))

    @extend_schema(request=DraftWriteSerializer, responses=ResourceDraftSerializer)
    def patch(self, request, graph_slug, pk):
        resource = self._get_or_404(request, pk)
        merged = {
            **self.store.to_record(resource).data,
            **(request.data or {}).get("data", {}),
        }
        self.verify_parent_resource_access(merged)
        return Response(self.serialize(self.store.set_data(resource, merged)))

    @extend_schema(responses={204: None})
    def delete(self, request, graph_slug, pk):
        self._get_or_404(request, pk).delete()
        return Response(status=204)
