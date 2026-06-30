"""Process Requirement API that widens the generated owner-scoped routes:
superusers and Resource Editors may read any instance, while everyone else stays
scoped to the resources they created.

Overrides the generated routes (see bcap.urls_api_documented), reusing the
generated serializer so the response shape stays in lockstep with the graph.
"""

from django.http import Http404

from drf_spectacular.utils import extend_schema, PolymorphicProxySerializer
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from arches.app.models.resource import Resource

from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ResourceEditor
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from arches_zod_validation.views.mixins import (
    BCAPResourceSerializer,
    UserOwnedResourceMixin,
)

from bcap.services.process_requirement.process_requirement_service import (
    ProcessRequirementService,
)
from bcap.services.process_requirement.template_specs import host_graph
from bcap.util.indexing import bulk_index
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.generated.process_requirement import ProcessRequirementViewMixin

RESOURCE_EDITOR_GROUP = "Resource Editor"


# Module host serializers. These graphs expose no generated routes of their own
# (their verbs are [] in generate.json); a host is only ever created through this
# view's POST, so the serializers live here rather than in the generated package.
class InvestigationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = "investigation"


class AlterationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = "alteration"


class InspectionSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = "inspection"


# The serializer that validates and creates a module's host resource, by host
# graph slug. A module names its host via the child whose resource matches the
# module slug (see template_specs.host_graph); a slug with no group file or no
# host child is rejected before the serializer is reached.
HOST_SERIALIZERS = {
    "investigation": InvestigationSerializer,
    "alteration": AlterationSerializer,
    "inspection": InspectionSerializer,
}


def _module_host_schema(many):
    """OpenAPI schema for a module host: any one of the registered host types
    (the concrete type depends on the permit_type path segment)."""
    return PolymorphicProxySerializer(
        component_name="ModuleHost",
        serializers=list(HOST_SERIALIZERS.values()),
        resource_type_field_name=None,
        many=many,
    )


class SuperuserOrEditorReadsAnyMixin(UserOwnedResourceMixin):
    """Owner-scope the queryset like the base mixin, but let superusers and
    Resource Editors read any instance -- they review every requirement, not
    only the ones they created."""

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name=RESOURCE_EDITOR_GROUP).exists():
            # Skip the owner filter; fall through to the full graph queryset.
            return super(UserOwnedResourceMixin, self).get_queryset()
        return super().get_queryset()


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementListView(
    ProcessRequirementViewMixin,
    SuperuserOrEditorReadsAnyMixin,
    ArchesModelAPIMixin,
    ListAPIView,
):
    """Collection endpoint: superusers and Resource Editors see every Process
    Requirement; other users see only the ones they created."""

    permission_classes = [IsAuthenticated]
    pagination_class = ArchesLimitOffsetPagination


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementView(
    ProcessRequirementViewMixin,
    SuperuserOrEditorReadsAnyMixin,
    ArchesModelAPIMixin,
    RetrieveUpdateDestroyAPIView,
):
    """Detail endpoint: superusers and Resource Editors may read any instance;
    other users requesting one they don't own get a 404."""

    permission_classes = [IsAuthenticated]


@extend_schema(tags=["External: process_requirement"])
class ProcessRequirementSeedView(APIView):
    """POST: submit a permit module (a group of process requirements). The
    module's host resource (the child whose resource matches the permit type,
    e.g. investigation) is created from the request body and validated by its own
    serializer, the group's process requirements are cloned and attached to the
    permit, and the host submission requirement is linked to the created host.
    The created host is returned.

    The permit type is a path segment; a type with no host resource is a 400."""

    permission_classes = [ResourceEditor]

    def _host_serializer_class(self, permit_type, pk):
        """The serializer for the module's host resource. 400 when the type has
        no host; 404 when the permit application is unknown."""
        serializer_class = (
            HOST_SERIALIZERS.get(permit_type) if host_graph(permit_type) else None
        )
        if serializer_class is None:
            raise ValidationError(f"Module '{permit_type}' has no host resource.")
        if not ResourceTileTree.objects.filter(
            pk=pk, graph__slug=GraphSlugs.PERMIT_APPLICATION
        ).exists():
            raise Http404("No permit application matches the given id.")
        return serializer_class

    @extend_schema(responses=_module_host_schema(many=True))
    def get(self, request, pk, permit_type):
        """The module's host resources attached to the permit application."""
        serializer_class = self._host_serializer_class(permit_type, pk)
        hosts = ProcessRequirementService(user=request.user).permit_module_hosts(
            pk, permit_type
        )
        return Response(
            [serializer_class(host, request=request).data for host in hosts]
        )

    @extend_schema(
        request=_module_host_schema(many=False),
        responses=_module_host_schema(many=False),
    )
    def post(self, request, pk, permit_type):
        serializer_class = self._host_serializer_class(permit_type, pk)
        host_serializer = serializer_class(data=request.data, request=request)
        host_serializer.is_valid(raise_exception=True)
        host = host_serializer.save()
        host_resource = Resource.objects.get(pk=host.pk)
        host_resource.save_descriptors()
        ProcessRequirementService(user=request.user).attach_requirements(
            pk, permit_type, host
        )
        bulk_index([host_resource])
        # Re-read the saved host as representation so the response carries
        # display_value (what the review screen renders).
        fresh = ResourceTileTree.get_tiles(
            host_graph(permit_type), resource_ids=[host.pk], as_representation=True
        ).get()
        return Response(serializer_class(fresh, request=request).data, status=201)
