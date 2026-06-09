"""Shared view mixins and serializer bases for BCAP resource APIs."""

from drf_spectacular.utils import extend_schema_field, extend_schema_serializer
from rest_framework.authentication import SessionAuthentication

from arches_querysets.rest_framework.serializers import ArchesResourceSerializer
from arches_querysets.utils.models import ensure_request

from bcap.schema import ArchesTileAutoSchema


@extend_schema_serializer(description="")
class BCAPResourceSerializer(ArchesResourceSerializer):
    """Base for the per-graph resource serializers; subclasses set
    Meta.graph_slug. Re-declares get_graph_has_different_publication only to
    annotate its bool return type for the OpenAPI generator."""

    @extend_schema_field(bool)
    def get_graph_has_different_publication(self, obj):
        return super().get_graph_has_different_publication(obj)


class ArchesResourceViewMixin:
    """Auth, schema, and the swagger_fake_view serializer fix shared by the BCAP
    resource APIs. Must precede the DRF generic view in the MRO so its
    get_serializer wins; each view supplies its own serializer_class."""

    authentication_classes = [SessionAuthentication]
    schema = ArchesTileAutoSchema()

    def get_serializer(self, *args, **kwargs):
        # During schema introspection the serializer can't resolve nodegroups
        # without a real user, so supply the admin user to get the full field list.
        if getattr(self, "swagger_fake_view", False):
            return self.get_serializer_class()(
                *args, request=ensure_request(None, force_admin=True)
            )
        return super().get_serializer(*args, **kwargs)


class UserOwnedResourceMixin:
    """Restrict the resource queryset to instances created by the requesting user.

    Filters on the Arches `principaluser` (the creating user), so a detail GET
    for a resource the user doesn't own returns 404 rather than another user's
    data. Must precede arches_querysets' ArchesModelAPIMixin in the MRO so its
    get_queryset is the one being extended.
    """

    def get_queryset(self):
        return super().get_queryset().filter(principaluser=self.request.user)
