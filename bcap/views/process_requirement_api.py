"""Process Requirement GET/PUT/PATCH/DELETE via arches_querysets' generic resource serializer."""

from drf_spectacular.utils import extend_schema

from arches_querysets.rest_framework.generic_views import ArchesResourceDetailView

from bcap.views.mixins import ArchesResourceViewMixin

# Reuse the generated serializer so there's a single "ProcessRequirement" OpenAPI
# component; two same-named serializer classes break the schema (drf-spectacular).
from bcap.views.generated.process_requirement import ProcessRequirementSerializer


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
