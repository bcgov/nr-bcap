"""Read-only HCA Permit API, scoped to the requesting user's own permits:
a list of the user's permits and a by-id detail fetch."""

from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated

from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin
from arches_querysets.utils.models import ensure_request

from bcap.schema import ArchesTileAutoSchema
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.mixins import UserOwnedResourceMixin


class HCAPermitSerializer(ArchesResourceSerializer):
    class Meta(ArchesResourceSerializer.Meta):
        graph_slug = GraphSlugs.HCA_PERMIT

    @extend_schema_field(bool)
    def get_graph_has_different_publication(self, obj):
        return super().get_graph_has_different_publication(obj)


class HCAPermitViewMixin:
    """Shared config for the HCA Permit detail view.

    Carries the serializer, auth, schema, and the swagger_fake_view serializer
    fix. Must precede the DRF generic view in the MRO so its get_serializer wins.
    """

    authentication_classes = [SessionAuthentication]
    serializer_class = HCAPermitSerializer
    schema = ArchesTileAutoSchema()

    def get_serializer(self, *args, **kwargs):
        # During schema introspection the serializer can't resolve nodegroups
        # without a real user, so supply the admin user to get the full field list.
        if getattr(self, "swagger_fake_view", False):
            return self.get_serializer_class()(
                *args, request=ensure_request(None, force_admin=True)
            )
        return super().get_serializer(*args, **kwargs)


@extend_schema(tags=["External: hca_permit"])
class HCAPermitListView(
    HCAPermitViewMixin,
    UserOwnedResourceMixin,
    ArchesModelAPIMixin,
    ListAPIView,
):
    """GET the requesting user's HCA Permits.

    Read-only and owner-scoped: returns only the permits the user created.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = ArchesLimitOffsetPagination


@extend_schema(tags=["External: hca_permit"])
class HCAPermitView(
    HCAPermitViewMixin,
    UserOwnedResourceMixin,
    ArchesModelAPIMixin,
    RetrieveAPIView,
):
    """GET an HCA Permit and its nested tiles.

    Read-only, and scoped to the requesting user's own permits: requesting one
    created by another user returns 404.
    """

    permission_classes = [IsAuthenticated]
