"""Custom drf-spectacular AutoSchema subclasses for bcap views."""

import logging

from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers

from arches_querysets.rest_framework.field_mixins import NodeValueMixin
from arches_querysets.rest_framework.serializers import TileAliasedDataSerializer

logger = logging.getLogger(__name__)


class NodeValueEnvelopeSerializer(serializers.Serializer):
    """The {node_value, display_value, details} object node value fields emit when as_representation is True.

    Mirrors the dict built in arches_querysets TileTree.get_value_with_context;
    keep in sync if that shape changes upstream (unit test covers this).
    """

    node_value = serializers.JSONField()
    display_value = serializers.CharField(read_only=True)
    details = serializers.ListField(child=serializers.DictField(), read_only=True)


class NodeValueFieldExtension(OpenApiSerializerFieldExtension):
    """Map node value fields to the shared NodeValueEnvelope component."""

    target_class = NodeValueMixin
    match_subclasses = True

    def map_serializer_field(self, auto_schema, direction):
        # Pass the class; resolve_serializer force-instances it.
        return auto_schema.resolve_serializer(
            NodeValueEnvelopeSerializer, direction
        ).ref


class ArchesTileAutoSchema(AutoSchema):
    """Key each TileAliasedData component name off its nodegroup so drf-spectacular doesn't collapse them all into one."""

    def get_serializer_name(self, serializer, direction):
        if isinstance(serializer, TileAliasedDataSerializer):
            # Resolving .fields runs the DB introspection that pins _root_node
            # to the nodegroup's grouping Node.
            try:
                serializer.fields
            except Exception:
                # Falls through to the default name below; log so a silently
                # un-specialized component name is still traceable.
                logger.debug(
                    "Could not resolve fields for %s; component name not "
                    "specialized by nodegroup.",
                    getattr(serializer, "graph_slug", serializer),
                    exc_info=True,
                )
            root_node = getattr(serializer, "_root_node", None)
            alias = getattr(root_node, "alias", root_node)
            if alias and serializer.graph_slug:
                # Match the "_"-joined Titlecase style of the tile components.
                return f"{serializer.graph_slug}_{alias}_aliased_data".title()
        return super().get_serializer_name(serializer, direction)
