"""Generic per-user draft storage: unvalidated form state for any graph as one
JSON blob, keyed by user + graph slug. The front end PUT/PATCHes `data`, GETs it
back to rehydrate on resume, then POSTs to the resource's create view to submit
(validated only then) and DELETEs the draft.

File uploads are held by reference: the front end uploads to Arches' `/temp_file`
(bytes in `files_temporary`, unattached) and keeps the `file_id` + file-list
metadata in `data`. GOTCHA: Arches won't auto-promote a TempFile's bytes into a
resource `File`, so submit must re-send the files via multipart or copy the bytes
across itself (and bcap's FILENAME_GENERATOR needs the tile to build the path)."""

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView

from bcap.models.resource_draft import ResourceDraft
from bcap.permissions.groups import Groups
from bcap.permissions.route_permissions import any_groups_required
from bcap.util.graph import get_current_graph


class ResourceDraftSerializer(serializers.ModelSerializer):
    graph_has_different_publication = serializers.SerializerMethodField()

    class Meta:
        model = ResourceDraft
        exclude = ["user"]  # owner is set server-side, never client-supplied
        # Stamped on create (id/updated already read-only via field options).
        read_only_fields = ["graph_slug", "graph_publication_id", "created"]

    def get_graph_has_different_publication(self, obj) -> bool:
        """True when the published graph has moved on since the draft was saved."""
        if obj.graph_publication_id is None:
            return False
        graph = get_current_graph(obj.graph_slug)
        return bool(graph) and graph.publication_id != obj.graph_publication_id


class ResourceDraftViewMixin:
    authentication_classes = [SessionAuthentication]
    serializer_class = ResourceDraftSerializer
    # Drafts are personal scratch data -- every verb (incl. GET) requires an
    # external applicant (Submitter) or a staff editor; owner-scoping below then
    # limits each user to their own.
    permission_classes = [any_groups_required(Groups.SUBMITTER, Groups.RESOURCE_EDITOR)]

    def get_queryset(self):
        # Owner-scoped: a user only sees their own drafts (superusers see all),
        # so another user's draft is simply not found.
        drafts = ResourceDraft.objects.filter(graph_slug=self.kwargs["graph_slug"])
        if self.request.user.is_superuser:
            return drafts
        return drafts.filter(user=self.request.user)


@extend_schema(tags=["External: resource_draft"])
class ResourceDraftListCreateView(ResourceDraftViewMixin, ListCreateAPIView):
    """GET the current user's drafts for a graph; POST a new draft."""

    def perform_create(self, serializer):
        graph = get_current_graph(self.kwargs["graph_slug"])
        serializer.save(
            user=self.request.user,
            graph_slug=self.kwargs["graph_slug"],
            graph_publication_id=getattr(graph, "publication_id", None),
        )


@extend_schema(tags=["External: resource_draft"])
class ResourceDraftDetailView(ResourceDraftViewMixin, RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE a single draft. PUT replaces the whole blob; PATCH
    shallow-merges by section key -- untouched sections are kept, but a section
    present in the body is replaced wholesale (no deep merge), so the client must
    send the complete section, not just changed fields within it."""

    def perform_update(self, serializer):
        if serializer.partial and "data" in serializer.validated_data:
            merged = {**serializer.instance.data, **serializer.validated_data["data"]}
            serializer.save(data=merged)
        else:
            serializer.save()
