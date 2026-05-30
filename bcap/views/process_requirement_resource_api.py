"""Process Requirement read/update endpoint, done the arches_querysets way.

arches_querysets' generic resource serializer already maps the whole tile tree
-- the requirement tile and its nested sub-requirement child tiles -- to JSON,
and ArchesResourceDetailView already implements GET/PUT/PATCH/DELETE over it.
Pinning the graph is the only thing this needs: the nested sub-requirements are
saved by the serializer, so there is no separate sub-requirement endpoint.
"""

from rest_framework.authentication import SessionAuthentication

from drf_spectacular.openapi import AutoSchema

from arches_querysets.rest_framework.generic_views import ArchesResourceDetailView
from arches_querysets.rest_framework.serializers import (
    ArchesResourceSerializer,
    TileAliasedDataSerializer,
)
from arches_querysets.utils.models import ensure_request

from bcap.util.bcap_aliases import GraphSlugs


class ArchesTileAutoSchema(AutoSchema):
    """Give every nodegroup's aliased_data its own schema component.

    arches_querysets builds one TileAliasedDataSerializer class for every
    nodegroup, so drf-spectacular names them all "TileAliasedData", collides
    them, and keeps only the first -- leaving every tile (sub_requirement
    included) showing the wrong fields. The serializer already introspects the
    database for each nodegroup's node aliases; we just key the component name
    off the resolved nodegroup so those distinct field sets survive.
    """

    def get_serializer_name(self, serializer, direction):
        if isinstance(serializer, TileAliasedDataSerializer):
            # Resolving .fields runs the DB introspection that pins _root_node
            # to the nodegroup's grouping Node.
            try:
                serializer.fields
            except Exception:
                pass
            root_node = getattr(serializer, "_root_node", None)
            alias = getattr(root_node, "alias", root_node)
            if alias and serializer.graph_slug:
                # Match the "_"-joined Titlecase style of the tile components.
                return f"{serializer.graph_slug}_{alias}_aliased_data".title()
        return super().get_serializer_name(serializer, direction)


class ProcessRequirementResourceSerializer(ArchesResourceSerializer):
    class Meta(ArchesResourceSerializer.Meta):
        graph_slug = GraphSlugs.PROCESS_REQUIREMENT


class ProcessRequirementResourceView(ArchesResourceDetailView):
    """GET/PUT/PATCH/DELETE a Process Requirement and its sub-requirements.

    PATCH applies a partial diff (only the tiles present in the body); PUT
    replaces. Either way the serializer saves the nested sub-requirement tiles.
    """

    # Session (cookie) auth only -- no HTTP Basic, matching the other bcap views.
    authentication_classes = [SessionAuthentication]
    serializer_class = ProcessRequirementResourceSerializer
    schema = ArchesTileAutoSchema()

    def get_serializer(self, *args, **kwargs):
        # drf-spectacular introspects with a mock AnonymousUser and a view whose
        # setup() never ran, so the generic serializer -- which builds its fields
        # off request.user.userprofile's viewable nodegroups -- can't bind and the
        # endpoint degrades to an opaque object. During introspection only, hand
        # it the arches admin user so the full tile tree lands in the schema.
        if getattr(self, "swagger_fake_view", False):
            return self.get_serializer_class()(
                *args, request=ensure_request(None, force_admin=True)
            )
        return super().get_serializer(*args, **kwargs)
