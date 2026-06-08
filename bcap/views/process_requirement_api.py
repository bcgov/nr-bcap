"""Process Requirement GET/PUT/PATCH/DELETE via arches_querysets' generic resource serializer."""

from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework.authentication import SessionAuthentication

from arches_querysets.rest_framework.generic_views import ArchesResourceDetailView
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.utils.models import ensure_request

from bcap.schema import ArchesTileAutoSchema
from bcap.util.bcap_aliases import GraphSlugs


class ProcessRequirementSerializer(ArchesResourceSerializer):
    class Meta(ArchesResourceSerializer.Meta):
        graph_slug = GraphSlugs.PROCESS_REQUIREMENT

    @extend_schema_field(bool)
    def get_graph_has_different_publication(self, obj):
        return super().get_graph_has_different_publication(obj)


class ProcessRequirementViewMixin:
    """Shared config for the Process Requirement detail view.

    Carries the serializer, auth, schema, and the swagger_fake_view serializer
    fix. Must precede the DRF generic view in the MRO so its get_serializer wins.
    """

    authentication_classes = [SessionAuthentication]
    serializer_class = ProcessRequirementSerializer
    schema = ArchesTileAutoSchema()

    def get_serializer(self, *args, **kwargs):
        # During schema introspection the serializer can't resolve nodegroups
        # without a real user, so supply the admin user to get the full field list.
        if getattr(self, "swagger_fake_view", False):
            return self.get_serializer_class()(
                *args, request=ensure_request(None, force_admin=True)
            )
        return super().get_serializer(*args, **kwargs)


@extend_schema(tags=["Internal: process_requirement"])
class ProcessRequirementView(ProcessRequirementViewMixin, ArchesResourceDetailView):
    """GET/PUT/PATCH/DELETE a Process Requirement and its sub-requirements.

    PATCH applies a partial diff (only the tiles present in the body); PUT
    replaces. Either way the serializer saves the nested sub-requirement tiles.

    Process Requirements are created internally (cloned from templates by the
    process_requirement service), not via a public POST, so there is no create
    route here.
    """
