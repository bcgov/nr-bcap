"""Permit Application CRUD via arches_querysets' generic resource serializer:
POST a new application, and GET/PUT/PATCH/DELETE an existing one."""

from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import JSONParser

from arches_querysets.rest_framework.generic_views import (
    ArchesResourceDetailView,
    ArchesModelAPIMixin,
)
from bcap.permissions.groups import Groups
from bcap.permissions.route_permissions import any_groups_required
from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.mixins import (
    ArchesResourceViewMixin,
    BCAPResourceSerializer,
    UserOwnedResourceMixin,
)


class PermitApplicationSerializer(BCAPResourceSerializer):
    class Meta(BCAPResourceSerializer.Meta):
        graph_slug = GraphSlugs.PERMIT_APPLICATION


class PermitApplicationViewMixin(ArchesResourceViewMixin):
    serializer_class = PermitApplicationSerializer


@extend_schema(tags=["External: permit_application"])
class PermitApplicationView(
    PermitApplicationViewMixin, UserOwnedResourceMixin, ArchesResourceDetailView
):
    """GET/PUT/PATCH/DELETE a Permit Application and its nested tiles.

    Scoped to the requesting user's own applications: requesting one created by
    another user returns 404.

    PATCH applies a partial diff (only the tiles present in the body); PUT
    replaces.
    """

    permission_classes = [any_groups_required(Groups.SUBMITTER, Groups.RESOURCE_EDITOR)]


@extend_schema(tags=["External: permit_application"])
class PermitApplicationCreateView(
    PermitApplicationViewMixin, ArchesModelAPIMixin, CreateAPIView
):
    """POST a new Permit Application.

    Create-only: CreateAPIView exposes just POST (and OPTIONS); there is no
    list/GET route.
    """

    permission_classes = [any_groups_required(Groups.SUBMITTER, Groups.RESOURCE_EDITOR)]
    parser_classes = [JSONParser]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        return PermitApplicationService().create_application(
            request.data,
            save_application=lambda: super(PermitApplicationCreateView, self).create(
                request, *args, **kwargs
            ),
        )
