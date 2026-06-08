"""Permit Application CRUD via arches_querysets' generic resource serializer:
POST a new application, and GET/PUT/PATCH/DELETE an existing one."""

from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import CreateAPIView
from rest_framework.parsers import JSONParser

from arches_querysets.rest_framework.generic_views import (
    ArchesResourceDetailView,
    ArchesModelAPIMixin,
)
from arches_querysets.rest_framework.permissions import ReadOnly, ResourceEditor
from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.utils.models import ensure_request

from bcap.schema import ArchesTileAutoSchema
from bcap.services.permit_application.permit_application_service import (
    PermitApplicationService,
)
from bcap.util.bcap_aliases import GraphSlugs
from bcap.views.mixins import UserOwnedResourceMixin


class PermitApplicationSerializer(ArchesResourceSerializer):
    class Meta(ArchesResourceSerializer.Meta):
        graph_slug = GraphSlugs.PERMIT_APPLICATION

    @extend_schema_field(bool)
    def get_graph_has_different_publication(self, obj):
        return super().get_graph_has_different_publication(obj)


class PermitApplicationViewMixin:
    """Shared config for the Permit Application detail and create views.

    Carries the serializer, auth, schema, and the swagger_fake_view serializer
    fix. Must precede the DRF generic view in the MRO so its get_serializer wins.
    """

    authentication_classes = [SessionAuthentication]
    serializer_class = PermitApplicationSerializer
    schema = ArchesTileAutoSchema()

    def get_serializer(self, *args, **kwargs):
        # During schema introspection the serializer can't resolve nodegroups
        # without a real user, so supply the admin user to get the full field list.
        if getattr(self, "swagger_fake_view", False):
            return self.get_serializer_class()(
                *args, request=ensure_request(None, force_admin=True)
            )
        return super().get_serializer(*args, **kwargs)


@extend_schema(tags=["permit_application"])
class PermitApplicationView(
    PermitApplicationViewMixin, UserOwnedResourceMixin, ArchesResourceDetailView
):
    """GET/PUT/PATCH/DELETE a Permit Application and its nested tiles.

    Scoped to the requesting user's own applications: requesting one created by
    another user returns 404.

    PATCH applies a partial diff (only the tiles present in the body); PUT
    replaces.
    """


@extend_schema(tags=["permit_application"])
class PermitApplicationCreateView(
    PermitApplicationViewMixin, ArchesModelAPIMixin, CreateAPIView
):
    """POST a new Permit Application.

    Create-only: CreateAPIView exposes just POST (and OPTIONS); there is no
    list/GET route.
    """

    permission_classes = [ResourceEditor]
    parser_classes = [JSONParser]
    http_method_names = ["post", "options"]

    def create(self, request, *args, **kwargs):
        return PermitApplicationService().create_application(
            request.data,
            save_application=lambda: super(PermitApplicationCreateView, self).create(
                request, *args, **kwargs
            ),
        )
