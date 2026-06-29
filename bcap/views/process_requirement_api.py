"""Process Requirement API that widens the generated owner-scoped routes:
superusers and Resource Editors may read any instance, while everyone else stays
scoped to the resources they created.

Overrides the generated routes (see bcap.urls_api_documented), reusing the
generated serializer so the response shape stays in lockstep with the graph.
"""

from django.http import Http404

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from arches_querysets.models import ResourceTileTree
from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.permissions import ResourceEditor
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from arches_zod_validation.views.mixins import UserOwnedResourceMixin

from bcap.services.process_requirement.process_requirement_seed_service import (
    PERMIT_TYPES,
    ProcessRequirementSeedService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.generated.process_requirement import ProcessRequirementViewMixin

RESOURCE_EDITOR_GROUP = "Resource Editor"


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
    """POST: seed the four process requirements for a permit type onto a permit
    application, each linked to a freshly created module resource where the type
    calls for one, plus an unattached grouping parent. The permit type is a path
    segment (inspection / investigation / alteration)."""

    permission_classes = [ResourceEditor]

    def post(self, request, pk, permit_type):
        if permit_type not in PERMIT_TYPES:
            return Response(
                {"detail": f"Unknown permit type '{permit_type}'."}, status=400
            )
        if not ResourceTileTree.objects.filter(
            pk=pk, graph__slug=GraphSlugs.PERMIT_APPLICATION
        ).exists():
            raise Http404("No permit application matches the given id.")
        result = ProcessRequirementSeedService(user=request.user).seed(pk, permit_type)
        return Response(
            {
                "parent": str(result["parent"].pk),
                "requirements": [str(r.pk) for r in result["requirements"]],
            },
            status=201,
        )
