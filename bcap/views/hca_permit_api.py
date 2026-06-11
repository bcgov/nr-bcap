"""Read-only HCA Permit API, scoped to the requesting user's own permits:
a list of the user's permits and a by-id detail fetch."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView

from arches_querysets.rest_framework.pagination import ArchesLimitOffsetPagination
from arches_querysets.rest_framework.view_mixins import ArchesModelAPIMixin

from bcap.permissions.groups import Groups
from bcap.permissions.route_permissions import any_groups_required
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.mixins import (
    ArchesResourceViewMixin,
    BCAPResourceSerializer,
    UserOwnedResourceMixin,
)


class HCAPermitSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = GraphSlugs.HCA_PERMIT


class HCAPermitViewMixin(ArchesResourceViewMixin):
    serializer_class = HCAPermitSerializer


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

    permission_classes = [any_groups_required(Groups.SUBMITTER, Groups.RESOURCE_EDITOR)]
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

    permission_classes = [any_groups_required(Groups.SUBMITTER, Groups.RESOURCE_EDITOR)]
