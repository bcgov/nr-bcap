"""Process Requirement GET/PUT/PATCH/DELETE via arches_querysets' generic resource serializer."""

from drf_spectacular.utils import extend_schema

from arches_querysets.rest_framework.generic_views import ArchesResourceDetailView

from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.mixins import ArchesResourceViewMixin, BCAPResourceSerializer


class ProcessRequirementSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = GraphSlugs.PROCESS_REQUIREMENT


class ProcessRequirementViewMixin(ArchesResourceViewMixin):
    serializer_class = ProcessRequirementSerializer


@extend_schema(tags=["Internal: process_requirement"])
class ProcessRequirementView(ProcessRequirementViewMixin, ArchesResourceDetailView):
    """GET/PUT/PATCH/DELETE a Process Requirement and its sub-requirements.

    PATCH applies a partial diff (only the tiles present in the body); PUT
    replaces. Either way the serializer saves the nested sub-requirement tiles.

    Process Requirements are created internally (cloned from templates by the
    process_requirement service), not via a public POST, so there is no create
    route here.
    """
