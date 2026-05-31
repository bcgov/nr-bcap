"""Custom drf-spectacular AutoSchema subclasses for bcap views."""

from drf_spectacular.openapi import AutoSchema

from arches_querysets.rest_framework.serializers import TileAliasedDataSerializer


class ArchesTileAutoSchema(AutoSchema):
    """Key each TileAliasedData component name off its nodegroup so drf-spectacular doesn't collapse them all into one."""

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
